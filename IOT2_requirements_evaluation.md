# IoT.2 Requirements Evaluation — samples/mockup

For each extracted PICMG IoT.2 `shall` requirement, this file records PASS or FAIL and gives evidence only for FAILs or when a requirement is untestable from a static mockup.

Format: `<REQ #>` Requirement summary — PASS|FAIL|UNVERIFIABLE — Evidence or failing resource paths / notes

## Bridging / Aggregation (not applicable to mockup)

1. A bridged service shall provide a Redfish service on the upstream interface. 
    — UNVERIFIABLE
2. A bridged service shall communicate to lower-level Redfish services as a Redfish client. 
    — UNVERIFIABLE
3. A Redfish-PLDM bridge service shall provide a Redfish service on the upstream interface. 
    — UNVERIFIABLE
4. A Redfish-PLDM bridge service shall implement a PLDM agent to communicate to lower-level PLDM devices. 
    — UNVERIFIABLE

## Chassis Resources

5. Each IIoT.1 endpoint shall have one and only one Redfish Chassis resource associated with it.
	- Result: PASS

6. The Chassis resource shall define one value for the Links.AutomationNodes collection referencing the AutomationNode.
	- Result: PASS

7. FRU mapping: IIoT.1 FRU fields (AssetTag, DateOfManufacture, SerialNumber, Manufacturer, Model, PartNumber, SKU, Version) shall be mapped to Chassis fields (if FRU exists).
	- Result: TODO — Partial: mockup Chassis include `AssetTag`, `SerialNumber`, `Manufacturer`, `Model`, `PartNumber` but are missing `DateOfManufacture`, `SKU`, `Version` (ref example: samples/mockup/redfish/v1/Chassis/XAxisMover/index.json).

8. The Chassis `ChassisType` shall be "Module" for AutomationNode-associated Chassis.
	- Result: PASS

9. The Chassis `Controls` field shall be present if there are any Controls associated.
	- Result: PASS

10. If present, the Chassis `Controls` field shall point to a valid ControlCollection resource.
	- Result: PASS

11. The Chassis `Sensors` field shall be present if there are any Sensors associated.
	- Result: PASS

12. If present, the Chassis `Sensors` field shall point to a valid SensorCollection resource.
	- Result: PASS

## Sensor and Control Resources

13. All numeric sensors present in the IIoT.1 node shall be present in the Chassis Sensor collection.
	- Result: PASS

14. Sensor IDs for IIoT.1-associated sensors shall be `SENSOR_ID_x`.
	- Result: PASS

15. Sensor IDs not associated with IIoT.1 nodes shall utilize a different naming convention.
	- Result: PASS

16. All numeric effecters in IIoT.1 node shall be present in the Chassis Control collection.
	- Result: PASS

17. Control IDs for IIoT.1-associated controls shall be `EFFECTER_ID_x`.
	- Result: PASS

18. Control IDs not associated with IIoT.1 nodes shall utilize a different naming convention.
	- Result: PASS

19. Writing SetPoint values to controls shall be reflected in the `PendingSetPoint` field until such time that the Control begins using the new SetPoint.
	- Result: ERRATA — Runtime behavior; static mockups do not show `PendingSetPoint` updates.
    - Resolution: The ERRATA will remove this requirement.  If readback is desired, operators may add another sensor that shows the operational value for the SetPoint, where the control SetPoint value will have standard behavior. 

20. If node has pfinal (effecter ID 4) and position sensor (sensor ID 7), Control.Sensor for pfinal shall reference the position Sensor.
	- Result: PASS

21. If node has vprofile (effecter ID 5), Control.Sensor for vprofile shall only be present if AutomationNode NodeType is `MotionVelocity`.
	- Result: PASS

22. If vprofile (5) and velocity sensor (6), Control.Sensor for vprofile shall reference the velocity sensor if AutomationNode Type is `MotionVelocity`.
	- Result: UNVERIFIABLE.

## Sensor Threshold Mapping

23. IIoT.1 sensor thresholds shall map to canonical Redfish thresholds.
	- Result: PASS

## Global Interlock Mapping

24. Global Interlock sensor shall be `SENSOR_ID_1`.
	- Result: PASS

25. Locked state -> Sensor returns `1`.
	- Result: PASS

26. Unlocked state -> Sensor returns `0`.
	- Result: PASS

27. Global Interlock effecter shall be `EFFECTER_ID_1`.
	- Result: PASS

28. Setting setpoint to `1` shall set effecter to Locked state.
	- Result: UNVERIFIABLE

29. Setting setpoint to `0` shall set effecter to Unlocked state.
	- Result: UNVERIFIABLE

30. Controller for Global Interlock shall only accept SetPoint values `0` or `1`.
	- Result: PASS

## Limit Sensors (Positive/Negative Limit)

31. PositiveLimit sensor (if present) shall be `SENSOR_ID_8`.
	- Result: PASS

32. When PositiveLimit pressed -> Sensor returns `1`.
	- Result: PASS

33. When PositiveLimit released -> Sensor returns `0`.
	- Result: PASS

34. NegativeLimit sensor (if present) shall be `SENSOR_ID_9`.
	- Result: PASS

35. When NegativeLimit pressed -> Sensor returns `1`.
	- Result: PASS

36. When NegativeLimit released -> Sensor returns `0`.
	- Result: PASS

## Assembly Resources

37. Additional FRU info shall be stored in an AssemblyData resource referenced by the Chassis (if Assembly exists).
	- Result: UNVERIFIABLE

38. FRU info stored in AssemblyData shall use the AssemblyRecord mapping.
	- Result: UNVERIFIABLE

39. `BinaryDataURI` field of AssemblyData shall reference FRU binary blob.
	- Result: UNVERIFIABLE

## AutomationNode Resources

40. NodeType shall be `Simple` for IIoT.1 Vendor Entity ID `0001h`.
	- Result: UNVERIFIABLE

41. NodeType shall be `Pid` for Vendor Entity ID `0002h`.
	- Result: UNVERIFIABLE

42. NodeType shall be `MotionPosition` for Vendor Entity ID `0003h` intended for PI-V control.
	- Result: UNVERIFIABLE

43. NodeType shall be `MotionVelocity` for Vendor Entity ID `0003h` intended for velocity control.
	- Result: UNVERIFIABLE

44. The `Links.Chassis` field shall be present within the AutomationNode.
	- Result: PASS

## AutomationNode Actions and Behavior

45. All AutomationNodes shall support `AutomationNode.SendTrigger`.
	- Result: PASS

46. `AutomationNode.SendTrigger` shall cause a trigger pulse on IIoT.1 node.
	- Result: UNVERIFIABLE

47. Nodes with `PID`, `MotionPosition`, `MotionVelocity` shall support `AutomationNode.Start`.
	- Result: PASS

48. Use of `AutomationNode.Start` shall generate a Start command on the IIoT.1 node.
	- Result: UNVERIFIABLE

49. Nodes with `PID`, `MotionPosition`, `MotionVelocity` shall support `AutomationNode.Stop`.
	- Result: PASS

50. Use of `AutomationNode.Stop` shall generate a Stop command on the IIoT.1 node.
	- Result: UNVERIFIABLE

51. Nodes with `MotionPosition` or `MotionVelocity` shall support `AutomationNode.Wait`.
	- Result: PASS

52. Use of `AutomationNode.Wait` shall generate a Wait command on the IIoT.1 node.
	- Result: UNVERIFIABLE

53. The `NodeState` field shall indicate IIoT.1 node controller state using the specified strings.
	- Result: PASS

## AutomationInstrumentation

54. AutomationInstrumentation `NodeState` shall match AutomationNode `NodeState`.
	- Result: PASS

55. When AutomationNode is `MotionPosition`, the top-level `Position` field shall be present.
	- Result: ERRATA — `Position` appears under `Oem.PICMG.Position` in `AutomationInstrumentation`, not as a top-level `Position` field (ref file: samples/mockup/redfish/v1/AutomationNodes/XAxisMover/AutomationInstrumentation/index.json).
    - Resoultion: When AutomationNode is `MotionPosition`, the top-level `NodeControl` field shall be present. 

56. If `Position` field is present, its `DataSourceUri` shall reference Control for pfinal effecter.
	- Result: ERRATA — Top-level `Position` absent; vendor `Oem` contains a DataSourceUri but it's under `Oem`.
    - Resolution: When AutomationNode is `MotionPosition`, the `DataSourceUri` of the top level `NodeControl` shall reference Control for pfinal effecter.

57. Changing `Position` shall behave as if associated Control modified directly.
	- Result: ERRATA
    - Changing `SetPoint` field of the top-level `NodeControl` shall behave as if the associated Control was modified directly.

58. When AutomationNode is `MotionPosition`/`MotionVelocity`, `Velocity` field shall be present (top-level).
	- Result: ERRATA — `Velocity` only present under `Oem.PICMG` in mockup.
    - Resoultion: When AutomationNode is `MotionVelocity`, the top-level `NodeControl` field shall be present.

59. If `Velocity` present, its `DataSourceUri` shall reference vprofile effecter.
	- Result: ERRATA — Present under `Oem` only; top-level `Velocity` missing.
    - Resolution: When AutomationNode is `MotionVelocity`, the `DataSourceUri` of the top level `NodeControl` shall reference Control for vprofile effecter.
    NOTE: The Control associated with the vprofile effecter may be accessed directly whether or not this field is present.

60. Changing `Velocity` shall behave as if associated Control modified directly.
	- Result: ERRATA
    - Resolution: Remove this requirement.  It is redundant

61. When `MotionPosition`/`MotionVelocity`, `Acceleration` field shall be present (top-level).
	- Result: ERRATA — `Acceleration` only present under `Oem.PICMG` in mockup.
    - Resolution: Remove this requirement.
    NOTE: The Control associated with the aprofile effecter may be accessed directly whether or not this field is present.  

62. If `Acceleration` present, its `DataSourceUri` shall reference aprofile effecter.
	- Result: ERRATA — Present under `Oem` only; top-level field missing.
    - Resolution: Remove this requirement

63. Changing `Acceleration` shall behave as if associated Control modified directly.
	- Result: UNVERIFIABLE
    - Resolution: Remove this requirement

64. If node contains acceleration gain effecter, `AccelerationGain` field shall be present.
	- Result: UNVERIFIABLE.
    - Resolution: Remove this requirement.
    NOTE: The Control associated with the aprofile effecter may be accessed directly whether or not this field is present.  


65. If `AccelerationGain` present, its `DataSourceUri` shall reference AccelerationGain effecter.
	- Result: ERRATA.
    - Resolution: Remove this requirement.
    
66. Changing `AccelerationGain` shall behave as if associated Control modified directly.
	- Result: ERRATA.
    - Resolution: Remove this requirement.

67. When AutomationNode is `PID`, the `PID` field shall be present.
	- Result: PASS.

68. If `PID` present, its `DataSourceUri` shall reference the PID effecter.
	- Result: PASS.

69. Changing `PID` shall behave as if associated Control modified directly.
	- Result: PASS

## Insertion and Removal of IIoT.1 Nodes

70. `Status.State` of Chassis and AutomationNode not present shall be "Absent".
	- Result: UNVERIFIABLE
    
71. `Status.State` of Chassis and AutomationNode shall be "UnavailableOffline" if Sensors/Controls incompatible.
	- Result: UNVERIFIABLE
    
72. `Status` of required Sensors/Controls missing shall be `Absent`.
	- Result: UNVERIFIABLE
    
73. `Status` of required Sensors/Controls unexpectedly present shall be `UnavailableOffline`.
	- Result: UNVERIFIABLE.

74. `Status` of required Sensors/Controls present but not configured properly shall be `UnavailableOffline`.
	- Result: UNVERIFIABLE.

## Job Management / Controllers

75. PICMG IoT.2 Controllers shall implement a Redfish Service.
	- Result: PASS

76. Controller Redfish services shall include a JobService resource.
	- Result: PASS

77. The JobService shall support document-based jobs (`ServiceCapabilities.DocumentBasedJobs`).
	- Result: PASS

