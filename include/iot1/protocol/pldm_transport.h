#pragma once

#include <libpldm/platform.h>
#include <sermctp/LinuxMctpSerial.hpp>
#include <memory>
#include <map>
#include <mutex>
#include <future>
#include <thread>
#include <atomic>
#include <chrono>
#include <iostream>

namespace iot1::protocol {

/**
 * @class PldmTransport
 * @brief Thread-safe async PLDM message transport over MCTP serial
 * 
 * Handles:
 * - Instance ID allocation and demultiplexing
 * - Request/response correlation via instance ID
 * - Concurrent endpoint requests (async futures)
 * - Timeout detection and cleanup
 */
class PldmTransport {
private:
    struct PendingRequest {
        std::promise<std::vector<uint8_t>> response_promise;
        std::chrono::steady_clock::time_point timeout;
        uint8_t target_eid;
    };
    
    std::unique_ptr<iotorch::sermctp::LinuxMctpSerial> mctp;
    
    // Thread safety for pending requests map
    mutable std::mutex pending_lock;
    std::map<uint8_t, PendingRequest> pending;  // instance_id -> pending response
    
    // Instance ID allocation (atomic - thread-safe)
    std::atomic<uint8_t> next_instance_id{0};
    
    // Receive thread
    std::thread rx_thread;
    std::thread timeout_thread;
    std::atomic<bool> running{false};
    
    uint8_t local_eid;
    
    // Receive loop - runs in separate thread, continuously reads MCTP
    void receiveLoop();
    
    // Timeout cleanup thread - removes stale pending requests
    void timeoutCleanupLoop();
    
public:
    PldmTransport();
    ~PldmTransport();
    
    /**
     * Initialize MCTP serial transport
     * @param mctp_interface - MCTP interface name (e.g., "mctpif0")
     * @param local_eid - Local endpoint ID (e.g., 8)
     * @param peer_eids - List of peer EIDs to communicate with
     * @return true if initialized successfully
     */
    bool initialize(const std::string& mctp_interface,
                   uint8_t local_eid,
                   const std::vector<uint8_t>& peer_eids);
    
    /**
     * Shutdown transport and cleanup threads
     */
    void close();
    
    /**
     * Allocate next instance ID (thread-safe, atomic)
     * @return instance ID (0-31)
     */
    uint8_t allocateInstanceId();
    
    /**
     * Send PLDM request asynchronously
     * 
     * @param target_eid - Destination endpoint ID
     * @param request - Encoded PLDM request message
     * @param timeout_ms - Response timeout in milliseconds
     * @return Future that will contain the response when it arrives
     * 
     * @note Multiple threads can call this simultaneously
     * @note Response is matched to request via instance ID
     */
    std::future<std::vector<uint8_t>> sendAsync(
        uint8_t target_eid,
        const std::vector<uint8_t>& request,
        int timeout_ms = 5000);
    
    /**
     * Send PLDM request synchronously (blocking wrapper around sendAsync)
     * 
     * @param target_eid - Destination endpoint ID
     * @param request - Encoded PLDM request message
     * @param response - Output buffer for response
     * @param timeout_ms - Response timeout in milliseconds
     * @return true if response received successfully
     */
    bool sendAndWaitResponse(
        uint8_t target_eid,
        const std::vector<uint8_t>& request,
        std::vector<uint8_t>& response,
        int timeout_ms = 5000);
    
    /**
     * Get local endpoint ID
     */
    uint8_t getLocalEid() const { return local_eid; }
    
    /**
     * Get count of pending requests (for diagnostics)
     */
    int getPendingRequestCount() const;
    
    /**
     * Check if transport is initialized and running
     */
    bool isRunning() const { return running; }
};

}  // namespace iot1::protocol
