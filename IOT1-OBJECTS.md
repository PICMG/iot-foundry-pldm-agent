# Recommended C++ Objects for PICMG IoT.1 Specification

Based on analysis of the PICMG IoT.1 R1.0 specification, the following C++ object hierarchy is recommended.

## Architecture Overview

The PICMG IoT.1 specification defines:
- **Endpoints**: The terminus of an IIoT Network connection (source/destination for data)
- **Sensors**: Elements that perform measurements (physical or logical)
- **Effecters**: Elements that accept setpoints and generate effects
- **PDRs**: Platform Data Records that describe device capabilities
- **Controllers**: Complex devices managing sensors/effecters (PID, Profiled Motion, etc.)

---

## Core Object Hierarchy

### 1. Network & Endpoint Objects

```
Endpoint (base class)
├── SimpleEndpoint
├── PidControlEndpoint
├── ProfiledMotionControlEndpoint
└── CompositeEndpoint (multiple devices)

Node
├── PhysicalNode
└── LogicalNode

Entity
├── EntityType (enum)
└── EntityAssociation
```

**Key Classes:**
- `PldmTerminus` - PLDM endpoint identifier
- `EndpointCapabilities` - Describes what endpoint supports
- `EndpointStatus` - Current operational state
- `EndpointConfiguration` - Device configuration parameters

### 2. Sensor Objects

```
Sensor (base class)
├── EnumeratedSensor
│   └── StateSensor
├── BooleanFlagSensor
├── NumericSensor
│   ├── RateSensor
│   ├── IntervalSensor
│   ├── AnalogSensor
│   └── TemperatureSensor
└── QuadratureEncoderSensor

SensorReading (measurement data)
├── NumericReading
├── StateReading
└── BooleanReading

SensorPDR (Platform Data Record)
├── NumericSensorPDR
└── StateSensorPDR
```

**Key Classes:**
- `SensorDefinition` - JSON object defining sensor
- `SensorId` - Unique sensor identifier
- `SensorInit` - Initialization state
- `SensorThresholds` - Min/max/alarm values
- `MeasurementAccuracy` - Precision/scaling

### 3. Effecter Objects

```
Effecter (base class)
├── StateEffecter
│   ├── OnOffEffecter
│   ├── ValveEffecter
│   └── EnumeratedStateEffecter
└── NumericEffecter
    ├── RelativeEffecter (incremental commands)
    ├── AbsoluteEffecter (setpoint-based)
    └── AnalogEffecter

EffecterCommand (control signal)
├── StateCommand
├── NumericCommand
└── RelativeCommand

EffecterPDR (Platform Data Record)
├── NumericEffecterPDR
└── StateEffecterPDR
```

**Key Classes:**
- `EffecterDefinition` - JSON object defining effecter
- `EffecterId` - Unique effecter identifier
- `EffecterStatus` - Current state/position
- `EffecterInit` - Initialization state

### 4. PDR (Platform Data Records) Objects

```
PDR (base class, abstract)
├── TerminusLocatorPDR
├── EntityAssociationPDR
├── OemEntityIdPDR
├── FruRecordSetPDR
├── NumericSensorPDR
├── StateSensorPDR
├── NumericEffecterPDR
├── StateEffecterPDR
├── OemStateSensorPDR
├── OemStateEffecterPDR
└── InterconnectDevicePDR

PDRRepository
├── addPDR()
├── getPDR()
├── getPDRs()
└── updateChangeNumber()

PDRHeader
├── recordHandle
├── pdrHeaderVersion
├── pdrType
├── recordChangeNumber
└── dataLength
```

**Key Classes:**
- `GlobalInterlockSensorPDR` - Lock state sensor
- `GlobalInterlockEffecterPDR` - Lock state control
- `TriggerSensorPDR` - Trigger mechanism sensor
- `TriggerEffecterPDR` - Trigger mechanism control

### 5. Controller Objects (Complex Functions)

#### PID Controller
```
PidController (extends Endpoint)
├── PidControlLoop
├── PidParameters (Kp, Ki, Kd)
├── PidState
├── FeedbackSensor
├── ControlEffecter
└── PidStatus

PidControlPDR
├── PidControlStateSensorPDR
├── PidControlCommandEffecterPDR
├── PidControlStatePDR
└── PidControlOemStateSetPDR
```

**Key Parameters:**
- Proportional gain (Kp)
- Integral gain (Ki)
- Derivative gain (Kd)
- Setpoint
- Output limits
- Control mode

#### Profiled Motion Controller
```
ProfiledMotionController (extends Endpoint)
├── MotionProfile
│   ├── TrapezoidalProfile
│   └── LinearProfile
├── MotionState
├── MotorControl (primary effecter)
├── PositionFeedback (primary sensor)
├── LimitSwitches (secondary sensors)
│   ├── CenterFlag
│   ├── EndStop (left/right)
│   └── Interlock
└── MotionStatus

ProfiledMotionControlPDR
├── ProfiledMotionStateSensorPDR
├── ProfiledMotionCommandEffecterPDR
├── ProfiledMotionStatePDR
└── ProfiledMotionOemStateSetPDR
```

**Key Parameters:**
- Profile type (trapezoidal)
- Acceleration
- Velocity
- Deceleration
- Position setpoint
- Movement direction

### 6. Configuration Objects

```
Configuration (base class)
├── FruRecord
│   ├── FruField
│   ├── FruInformation
│   └── FruMetadata
├── LogicalEntity
│   ├── EntityMetadata
│   └── EntityAssociation
├── Channel
│   ├── ChannelType
│   ├── ElectricalInterface
│   └── PinUse
└── Parameter
    ├── NumericParameter
    └── EnumeratedParameter

ConfigFile (JSON)
├── ControllerCapabilities
├── Channels
├── FruRecords
├── LogicalEntities
├── IOBindings
├── SensorDefinitions
├── EffecterDefinitions
├── Parameters
└── OemStateSets
```

**Key Classes:**
- `IOBinding` - Maps sensors/effecters to channels
- `Linearization` - Scaling/unit conversion
- `AlertThreshold` - Sensor alarm triggers
- `ChannelElectricalInterface` - RS-422, analog, digital, etc.

### 7. OEM & State Set Objects

```
OemStateSet
├── OemStateSensorPDR
├── OemStateEffecterPDR
└── StateSetValue

StateSet
├── StateId
├── PossibleStates
└── StateDefinitions

OemStateSetValueRecord
├── pldmStateSetId
├── oemStateValue
└── stateDefinition

EventState (for global interlock/triggers)
├── Disabled
├── Enabled
├── Triggered
└── Error
```

**Key State Sets:**
- Global Interlock (Lock State) - StateSetID 96
- Trigger States
- PID Controller States
- Profiled Motion States

### 8. Messaging & Protocol Objects

```
PldmMessage (base class)
├── PldmRequest
└── PldmResponse

MessagePayload
├── GetStateSensorReading
├── SetNumericEffecterValue
├── GetPdrRepositoryInfo
├── GetPdr
├── SetStateEffecterStates
└── TriggerEvent

SensorEvent
├── SensorId
├── SensorEventClass
├── EventState
└── EventMessageControl

EffecterEvent
├── EffecterId
├── EffecterEventClass
├── EventState
└── EventMessageControl
```

### 9. Data Point & Parameter Objects

```
DataPoint
├── DataType (numeric, state, boolean)
├── Value
├── Timestamp
├── Status
└── Quality

Parameter (configuration)
├── ParameterType (numeric/enumerated)
├── Value
├── MinValue / MaxValue
├── StepSize
├── Unit
└── Description

ParameterRange
├── Minimum
├── Maximum
├── StepSize
├── DefaultValue
└── Unit
```

---

## Recommended Class Implementation Order

### Phase 1: Foundation (Core Infrastructure)
1. `PldmTerminus` - PLDM endpoint identifier
2. `PdrHeader` - PDR metadata
3. `PDR` (abstract base) - All PDRs inherit from this
4. `PDRRepository` - Store and manage PDRs
5. `Entity` and `EntityAssociation` - Basic entity model

### Phase 2: Basic Sensors & Effecters
6. `Sensor` (abstract base)
7. `NumericSensor` - Temperature, pressure, etc.
8. `StateSensor` - On/off, valve states, etc.
9. `Effecter` (abstract base)
10. `StateEffecter` - Digital outputs
11. `NumericEffecter` - Analog/setpoint outputs

### Phase 3: PDR Types
12. `TerminusLocatorPDR`
13. `EntityAssociationPDR`
14. `OemEntityIdPDR`
15. `NumericSensorPDR`
16. `StateSensorPDR`
17. `NumericEffecterPDR`
18. `StateEffecterPDR`

### Phase 4: Configuration & IO Binding
19. `Channel` - Physical/logical channels
20. `IOBinding` - Maps sensors/effecters to channels
21. `FruRecord` - Device identification
22. `Configuration` - Device config management

### Phase 5: Advanced Controllers
23. `PidController` - PID control loop
24. `ProfiledMotionController` - Motion control
25. `ControllerCapabilities` - Feature description
26. `ControllerState` - Runtime state machine

### Phase 6: Events & Messaging
27. `SensorEvent` - Sensor event reporting
28. `EffecterEvent` - Effecter event reporting
29. `EventGenerator` - Event creation
30. `PldmMessage` & derived classes - Protocol messages

### Phase 7: JSON Configuration
31. `SensorDefinition` - JSON schema
32. `EffecterDefinition` - JSON schema
33. `ConfigFile` - Load/parse configuration
34. `OemStateSet` - OEM state definitions

---

## Key Design Patterns

1. **Abstract Base Classes** - PDR, Sensor, Effecter inherit from abstract bases
2. **Factory Pattern** - PDRFactory, SensorFactory for object creation
3. **Repository Pattern** - PDRRepository for central storage
4. **Observer Pattern** - Events for sensor readings/effecter changes
5. **Strategy Pattern** - Different controller types (PID, Profiled Motion)
6. **Decorator Pattern** - Scaling/linearization wraps raw measurements

---

## File Organization Recommendation

```
src/
├── io1/
│   ├── endpoint/
│   │   ├── endpoint.h/cpp
│   │   ├── simple_endpoint.h/cpp
│   │   ├── pid_controller.h/cpp
│   │   └── profiled_motion_controller.h/cpp
│   ├── sensor/
│   │   ├── sensor.h/cpp
│   │   ├── numeric_sensor.h/cpp
│   │   ├── state_sensor.h/cpp
│   │   └── sensor_event.h/cpp
│   ├── effecter/
│   │   ├── effecter.h/cpp
│   │   ├── state_effecter.h/cpp
│   │   ├── numeric_effecter.h/cpp
│   │   └── effecter_event.h/cpp
│   ├── pdr/
│   │   ├── pdr.h/cpp
│   │   ├── pdr_repository.h/cpp
│   │   ├── pdr_types.h/cpp
│   │   └── pdr_factory.h/cpp
│   ├── config/
│   │   ├── configuration.h/cpp
│   │   ├── io_binding.h/cpp
│   │   ├── fru_record.h/cpp
│   │   └── config_file.h/cpp
│   ├── message/
│   │   ├── pldm_message.h/cpp
│   │   ├── sensor_event.h/cpp
│   │   └── message_factory.h/cpp
│   └── iot1_common.h
include/
└── iot1_public.h
```

This structure provides a scalable, modular approach to implementing the PICMG IoT.1 specification.
