# PLDM Transport Integration

This document explains how the PldmTransport class integrates with Endpoints, Sensors, Effecters, and Controllers.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PldmAgent (main.cpp)                        │
│  - Creates PldmTransport                                        │
│  - Creates Endpoints with transport reference                   │
│  - Runs daemon                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
       ┌────────▼────────┐        ┌────────▼────────┐
       │   Endpoint A    │        │   Endpoint B    │
       │  (Simple)       │        │  (PID Control)  │
       │  - transport    │        │  - transport    │
       │  - sensors[]    │        │  - effecters[]  │
       │  - effecters[]  │        │  - controllers[]│
       └────────┬────────┘        └────────┬────────┘
                │                           │
        ┌───────┴──────────┐        ┌──────┴───────────┐
        │                  │        │                  │
  ┌─────▼──┐        ┌─────▼──┐ ┌──▼────┐        ┌────▼────┐
  │Sensor 1│        │Sensor 2│ │Effect1│        │Effect2  │
  │ - trans│        │ - trans│ │- trans│        │- trans  │
  └────────┘        └────────┘ └───────┘        └─────────┘
        │                  │        │                  │
        └──────────────────┼────────┼──────────────────┘
                          │
                  ┌───────▼──────────┐
                  │  PldmTransport   │
                  │  - receiveLoop() │
                  │  - pending map   │
                  │  - MCTP serial   │
                  └────────┬─────────┘
                           │
                    ┌──────▼──────┐
                    │ Serial Port  │
                    │ (libsermctp) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────────┐
                    │ MCTP Bus        │
                    │ (EID routing)   │
                    └─────────────────┘
```

## How It Works

### 1. **Initialization (main.cpp)**

```cpp
// Create transport (singleton per agent)
auto transport = std::make_shared<iot1::protocol::PldmTransport>();
transport->initialize("mctpif0", 8, {20, 21, 22});

// Create endpoints with transport reference
auto endpoint = std::make_shared<iot1::endpoint::SimpleEndpoint>(8, "LocalEndpoint");
endpoint->setTransport(transport);
endpoint->initialize(config);

// Same for sensors, effecters
auto sensor = std::make_shared<iot1::sensor::NumericSensor>(0x10, "TempSensor");
sensor->setTransport(transport);
```

### 2. **Sending Messages (Async Pattern)**

When a sensor/effecter wants to send a PLDM message:

```cpp
// Sensor wants to read from remote endpoint (EID=20)
class NumericSensor : public Sensor {
    json readRemote(uint8_t target_eid) {
        if (!transport) return json{{"error", "No transport"}};
        
        // Allocate unique instance ID
        uint8_t instance_id = transport->allocateInstanceId();
        
        // Encode PLDM request with instance_id
        std::array<uint8_t, 256> msg_buf{};
        size_t req_len = sizeof(msg_buf);
        encode_get_sensor_reading_req(
            instance_id,                    // <- unique ID
            sensorId,
            reinterpret_cast<pldm_msg*>(msg_buf.data()),
            &req_len
        );
        
        // Send async - returns immediately with Future
        auto future = transport->sendAsync(
            target_eid,                     // EID=20
            std::vector<uint8_t>(msg_buf.begin(), msg_buf.begin() + req_len)
        );
        
        // Wait for response (only blocks when needed)
        try {
            auto response = future.get();   // Blocks here
            
            // Decode response
            uint8_t cc = 0;
            uint8_t data[8] = {0};
            decode_get_sensor_reading_resp(
                reinterpret_cast<pldm_msg*>(response.data()),
                response.size(), &cc, nullptr, data);
            
            return json{{"value", data[0]}};
        } catch (const std::exception& e) {
            return json{{"error", e.what()}};
        }
    }
};
```

### 3. **Message Routing (MCTP + Instance ID)**

**Send Phase:**
```
Endpoint A (EID=8)                      Transport Thread
    │                                        │
    ├─ allocateInstanceId() → 5             │
    │                                        │
    ├─ Encode request, set instance_id=5   │
    │                                        │
    ├─ sendAsync(target_eid=20, msg)       │
    │  ├─ Register promise[5] in map ◄────────┘
    │  ├─ Send to MCTP serial
    │  └─ Return future
    │
    └─ future.get() blocks...
```

**Receive Phase:**
```
MCTP RX Thread                          Response Handler
    │
    ├─ Receive message from EID=20
    │  ├─ Extract instance_id=5
    │  └─ Look up pending[5] in map
    │
    └─ Found! Promise[5].set_value(msg)
         │
         └─ future.get() unblocks
            └─ Returns to Endpoint A with response
```

## Thread Safety

The transport is **fully thread-safe** for concurrent operations:

1. **Instance ID Allocation**: `std::atomic<uint8_t>` - no lock needed
2. **Pending Map Access**: `std::mutex pending_lock` - protects map operations
3. **Promise Registration**: Always done BEFORE send() to avoid race conditions
4. **Timeout Cleanup**: Separate thread removes stale requests

## Example: Multiple Concurrent Requests

```cpp
// Endpoint A
auto future_a = sensor1.readRemote(20);  // Sends instance_id=5

// Endpoint B (simultaneously)
auto future_b = sensor2.readRemote(21);  // Sends instance_id=6

// Endpoint C (simultaneously)
auto future_c = effecter1.setCommand(22); // Sends instance_id=7

// Responses arrive in any order...
auto resp_b = future_b.get();  // Unblocks when response[6] arrives
auto resp_a = future_a.get();  // Unblocks when response[5] arrives
auto resp_c = future_c.get();  // Unblocks when response[7] arrives
```

Each response is routed to the correct endpoint via **instance ID matching**.

## Maximum Concurrent Requests

Instance ID space: 0-31 (5 bits) = **32 concurrent requests maximum**

If you exceed this, you'll get a warning and the oldest request will be overwritten. For typical sensor/control loops, 32 concurrent is more than sufficient.

## Error Handling

1. **Timeout**: Request not answered within `timeout_ms` (default 5000ms)
   - Timeout cleanup thread removes stale pending requests
   - Future throws `std::runtime_error("PLDM request timeout")`

2. **Send Failure**: MCTP send() fails
   - Exception caught and set in promise
   - Future throws `std::runtime_error("Send failed")`

3. **Unknown Instance ID**: Response arrives but no matching pending request
   - Logged to stderr
   - Message is dropped
   - Indicates protocol error or late response

## Configuration Example

```json
{
  "agent": {
    "eid": 8,
    "name": "pldm-agent"
  },
  "transport": {
    "interface": "mctpif0",
    "local_eid": 8,
    "peer_eids": [20, 21, 22],
    "timeout_ms": 5000
  },
  "endpoints": [
    {
      "eid": 8,
      "name": "LocalEndpoint",
      "type": "Simple",
      "sensors": [
        {
          "id": 0x10,
          "name": "TemperatureSensor",
          "type": "Numeric",
          "minValue": -40,
          "maxValue": 125,
          "units": "°C"
        }
      ]
    }
  ]
}
```

## API Summary

### PldmTransport Methods

```cpp
// Initialization
bool initialize(const std::string& mctp_interface,
               uint8_t local_eid,
               const std::vector<uint8_t>& peer_eids);

// Instance ID allocation (atomic, thread-safe)
uint8_t allocateInstanceId();

// Async send (recommended)
std::future<std::vector<uint8_t>> sendAsync(
    uint8_t target_eid,
    const std::vector<uint8_t>& request,
    int timeout_ms = 5000);

// Sync send (wrapper around sendAsync)
bool sendAndWaitResponse(
    uint8_t target_eid,
    const std::vector<uint8_t>& request,
    std::vector<uint8_t>& response,
    int timeout_ms = 5000);

// Diagnostics
int getPendingRequestCount() const;
bool isRunning() const;
uint8_t getLocalEid() const;

// Shutdown
void close();
```

### Using Transport in Your Classes

```cpp
// Set transport on any object
endpoint->setTransport(transport);
sensor->setTransport(transport);
effecter->setTransport(transport);
controller->setTransport(transport);

// Access transport
auto xport = sensor->getTransport();

// In methods, use the async pattern
auto future = xport->sendAsync(target_eid, encoded_msg);
auto response = future.get();  // Blocks until response
```

## Next Steps

1. ✅ PldmTransport implemented with thread-safe async messaging
2. ✅ Integrated into Endpoint/Sensor/Effecter/Controller base classes
3. Next: Add PLDM responder functionality (handling incoming requests)
4. Next: Add event handling for unsolicited events from remote endpoints
5. Next: Configuration file loading with transport initialization
