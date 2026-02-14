# PICMG IoT.2 — "Shall" Requirements (extracted)

This file summarizes all normative requirements in PICMG IoT.2 R1.00 that use the keyword "shall".

NOTE: Each item below is an extraction of the `REQ:` statements from
`references/PICMG_IOT_2_R1_0.txt` and presented verbatim (minor punctuation
normalization only).

## Bridging / Aggregation

1. A PICMG IoT.2 bridged service shall provide a Redfish service on the upstream interface.
2. A PICMG IoT.2 bridged service shall communicate to lower-level Redfish services as a Redfish client.
3. A PICMG IoT.2 Redfish-PLDM bridge service shall provide a Redfish service on the upstream interface.
4. A PICMG IoT.2 Redfish-PLDM bridge service shall implement a PLDM agent to communicate to lower-level PLDM devices.

## Chassis Resources

5. Each IIoT.1 endpoint shall have one and only one Redfish Chassis resource associated with it.
6. The Chassis resource shall define one value for the Links.AutomationNodes collection that references the AutomationNode resource associated with the IIoT.1 node.
7. The IIoT.1 node's FRU data information (if it exists) shall be mapped to the specified Chassis resource fields (AssetTag, DateOfManufacture, SerialNumber, Manufacturer, Model, PartNumber, SKU, Version).
8. The ChassisType field of the Redfish Chassis resource associated with an AutomationNode shall have the value "Module".
9. The Chassis resource' Controls field shall be present if there are any Controls associated with the Chassis.
10. If present, the Chassis resource's Controls field shall point to a valid ControlCollection resource.
11. The Chassis resource's Sensors field shall be present if there are any Sensors associated with the Chassis.
12. If present, the Chassis resource's Sensors field shall point to a valid SensorCollection resource.

## Sensor and Control Resources

13. All numeric sensors present in the PICMG IIoT.1 Node resource shall be present in the Chassis Sensor collection.
14. The ID field of sensors associated with the IIoT.1 Node resource shall have the form `SENSOR_ID_x`.
15. The ID field of Sensor resources that are not associated with the IIoT.1 Node shall utilize a different naming convention.
16. All numeric effecters present in the PICMG IIoT.1 Node resource shall be present in the Chassis Control collection.
17. The ID field of controls associated with the IIoT.1 Node resource shall have the form `EFFECTER_ID_x`.
18. The ID field of Control resources that are not associated with the IIoT.1 Node shall utilize a different naming convention.
19. Writing SetPoint values to controls shall be reflected in the `PendingSetPoint` field until such time that the Control begins using the new SetPoint.
20. If the IIoT.1 node has both a pfinal effecter (effecter ID 4) and a position sensor (sensor ID 7), the Sensor field of the Control associated with the pfinal effector shall reference the Sensor associated with the IIoT.1 position sensor.
21. If the IIoT.1 node has a vprofile effecter (effecter ID 5), the Sensor field of the Control associated with the vprofile effector shall only be present if the AutomationNode associated with the Control is of NodeType "MotionVelocity".
22. If the IIoT.1 node has both a vprofile effecter (effecter ID 5) and a velocity sensor (sensor ID 6), the Sensor field of the Control associated with the vprofile effector shall reference the Sensor associated with the IIoT.1 velocity sensor if the AutomationNode is of Type "MotionVelocity".

## Sensor Threshold Mapping

23. IIoT.1 sensor thresholds (if present) shall map to the following Redfish thresholds: `lowerThresholdWarning -> LowerCaution`, `lowerThresholdCritical -> LowerCritical`, `lowerThresholdFatal -> LowerFatal`, `upperThresholdWarning -> UpperCaution`, `upperThresholdCritical -> UpperCritical`, `upperThresholdFatal -> UpperFatal`.

## Global Interlock Mapping

24. The IIoT.1 Global Interlock state sensor shall be mapped to a Sensor resource with an Id value of `SENSOR_ID_1`.
25. When the IIoT.1 Global Interlock state sensor is in the Locked state, the corresponding Sensor resource shall return a value of `1`.
26. When the IIoT.1 Global Interlock state sensor is in the Unlocked state, the corresponding Sensor resource shall return a value of `0`.
27. The IIoT.1 Global Interlock state effecter shall be mapped to a Control resource with an Id value of `EFFECTER_ID_1`.
28. Setting the setpoint for the Controller associated with the IIoT.1 Global Interlock state effecter to a value of `1` shall set the Global Interlock state effecter to the Locked state.
29. Setting the setpoint for the Controller associated with the IIoT.1 Global Interlock state effecter to a value of `0` shall set the Global Interlock state effecter to the Locked state.
30. The Controller associated with the IIoT.1 Global Interlock state effecter shall only accept SetPoint values of `0` or `1`.

## Limit Sensors (Positive/Negative Limit)

31. The IIoT.1 PositiveLimit state sensor (if present) shall be mapped to a Sensor resource with an Id value of `SENSOR_ID_8`.
32. When the IIoT.1 PositiveLimit state sensor is in the Pressed/On state, the corresponding Sensor resource shall return a value of `1`.
33. When the IIoT.1 PositiveLimit state sensor is in the Released/Off state, the corresponding Sensor resource shall return a value of `0`.
34. The IIoT.1 NegativeLimit state sensor (if present) shall be mapped to a Sensor resource with an Id value of `SENSOR_ID_9`.
35. When the IIoT.1 NegativeLimit state sensor is in the Pressed/On state, the corresponding Sensor resource shall return a value of `1`.
36. When the IIoT.1 NegativeLimit state sensor is in the Released/Off state, the corresponding Sensor resource shall return a value of `0`.

## Assembly Resources

37. Additional FRU information shall be stored within an AssemblyData resource referenced by the AutomationNode’s Chassis resource (if the Assembly resource exists).
38. FRU information stored in the associated AssemblyData resource shall be stored according to the specified AssemblyRecord mapping table (EngineeringChangeLevel, Model, PartNumber, Producer, ProductionDate, SKU, SerialNumber, Vendor, Version).
39. The `BinaryDataURI` field of the AssemblyData resource shall reference the complete set of FRU records in binary format as received from the IIoT.1 node.

## AutomationNode Resources

40. The NodeType fields of the AutomationNode resource shall contain the value of `Simple` for IIoT.1 nodes with a Vendor Entity ID of `0001h` (Simple Sensor/Effecter).
41. The NodeType fields of the AutomationNode resource shall contain the value of `Pid` for IIoT.1 nodes with a Vendor Entity ID of `0002h` (PID Control).
42. The NodeType fields of the AutomationNode resource shall contain the value of `MotionPosition` for IIoT.1 nodes with a Vendor Entity ID of `0003h` (Profiled Motion Control) that are intended for PI-V control.
43. The NodeType fields of the AutomationNode resource shall contain the value of `MotionVelocity` for IIoT.1 nodes with a Vendor Entity ID of `0003h` (Profiled Motion Control) that are intended for velocity control.
44. The `Links.Chassis` field shall be present within the AutomationNode.

## AutomationNode Actions and Behavior

45. All AutomationNodes shall support the `AutomationNode.SendTrigger` action.
46. The `AutomationNode.SendTrigger` action shall cause a trigger pulse to be generated on the corresponding IIoT.1 node.
47. AutomationNodes with the NodeType of `PID`, `MotionPosition`, or `MotionVelocity` shall support the `AutomationNode.Start` action.
48. Use of the `AutomationNode.Start` action shall generate a Start command on the associated IIoT.1 node.
49. AutomationNodes with the NodeType of `PID`, `MotionPosition`, or `MotionVelocity` shall support the `AutomationNode.Stop` action.
50. Use of the `AutomationNode.Stop` action shall generate a Stop command on the associated IIoT.1 node.
51. AutomationNodes with the NodeType of `MotionPosition`, or `MotionVelocity` shall support the `AutomationNode.Wait` action.
52. Use of the `AutomationNode.Wait` action shall generate a Wait command on the associated IIoT.1 node.
53. The value of the `NodeState` field shall indicate the state of the IIoT.1 node’s controller expressed as a Redfish string (Idle, Done, Waiting, ConditionStop, ErrorStop, Running, RunningP, RunningV).

## AutomationInstrumentation

54. The value of the `NodeState` field shall match the value of the `NodeState` field in the AutomationInstrumentation resource’s AutomationNode resource.
55. When the AutomationNode is a `MotionPosition` type, the `Position` field shall be present.
56. If the `Position` field is present, its `DataSourceUri` value shall reference the Control associated with the IIoT.1 pfinal effecter.
57. Changing values within the `Position` field shall behave as if the associated Control resource were modified directly.
58. When the AutomationNode is a `MotionPosition`, or `MotionVelocity` type, the `Velocity` field shall be present.
59. If the `Velocity` field is present, its `DataSourceUri` value shall reference the Control associated with the IIoT node’s vprofile effecter.
60. Changing values within the `Velocity` field shall behave as if the associated Control resource were modified directly.
61. When the AutomationNode is a `MotionPosition`, or `MotionVelocity` type, the `Acceleration` field shall be present.
62. If the `Acceleration` field is present, its `DataSourceUri` value shall reference the Control associated with the IIoT node’s aprofile effecter.
63. Changing values within the `Acceleration` field shall behave as if the associated Control resource were modified directly.
64. If the IIoT.1 node contains an acceleration gain effecter, the `AccelerationGain` field shall be present.
65. If the `AccelerationGain` field is present, its `DataSourceUri` value shall reference the Control associated with the IIoT node’s AccelerationGain effecter.
66. Changing values within the `AccelerationGain` field shall behave as if the associated Control resource were modified directly.
67. When the AutomationNode is a `PID` type, the `PID` field shall be present.
68. If the `PID` field is present, its `DataSourceUri` value shall reference the Control associated with the IIoT.1 PID effecter.
69. Changing values within the `PID` field shall behave as if the associated Control resource were modified directly.

## Insertion and Removal of IIoT.1 Nodes

70. The `Status` field of both the Chassis resource and the AutomationNode resource associated with an IIoT.1 node that is not present in the system shall have a `State` value of "Absent".
71. The `Status` field of both the Chassis resource and the AutomationNode resource associated with an IIoT.1 node shall have a `State` value of "UnavailableOffline" if the Sensors/Controls associated with it are incompatible with the system operation.
72. The `Status` field of required Sensors/Controls that are missing from an IIoT.1-related chassis resource shall have a `Status.State` value of "Absent".
73. The `Status` field of required Sensors/Controls that are unexpectedly present in an IIoT.1-related chassis resource shall have a `Status.State` value of "UnavailableOffline".
74. The `Status` field of required Sensors/Controls that are present in an IIoT.1-related chassis resource but not configured properly shall have a `Status.State` value of "UnavailableOffline".

## Job Management / Controllers

75. PICMG IoT.2 Controllers shall implement a Redfish Service.
76. PICMG IoT.2 Controller Redfish services shall include a JobService resource.
77. The JobService resource of an IoT.2 Controller shall support document-based jobs, as indicated by its `ServiceCapabilities.DocumentBasedJobs` field.

