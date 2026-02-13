# Overview
This document describes how to add AutomationNode, and related objects to a mockup using PDR data and IoT.2 requirements.  The portions of the device tree impacted are outlined in the figure below.
```
redfish
 |- v1
    |- Automation Nodes
    |   |-> add automation nodes
    |- Cables
    |   |-> Add automation node cables
    |- Chassis
    |   |- AggregatorChassis
    |   |- --> add Automation Node Chassis
    |- Systems
        |- AggregationSystem
            |- USBControllers
                 |- --> add Automation USBController
                           |- --> add Automation Node Usb Ports
```
# General requirements
- PDR and FRU data has been obtained from the device which conforms to the json format created by this project.
    - the PDR and FRU data has been stored in a file hereby referred to as `pdr_file` (actual filename and path may differ)
- Any resources must be of a type that is compliant with the current Redfish Schema.  Schema are found in the SchemaFiles/ folder off of the project root.
- When generating a new resource, it must contain all required field as specified in the resource schema.
- When generating a new resource that resides in a resource collection, the resource `@odata.id` must be added to the collections `Members[]` list.
- When generating a new resource that resides in a resource collection, the `Members@odata.count` value must be incremented by one.
- The value of the `@odata.context` field of a newly created resource must point to the schema of the newly created resource within relative to the mockup tree.  For example: `/redfish/v1/$metadata#ControlCollection.ControlCollection`,
- The value of the `@odata.id` for the newly created resource must point to the path of the resource within the mockup tree.  For example: `/redfish/v1/Chassis/Thermostat/Controls`
- resource files are always named `index.json`

# Step 1 - Cleaning
- The `new mockup` shall be created from a `reference mockup`
- The `reference mockup` shall not be altered in any way during `new mockup` creation
- the `new mockup` shall be placed in a folder of the users choosing (a default may be suggested)
- if the `new mockup` folder already exists, the user shall be asked if the folder can be deleted.  If the user responds `Yes` the folder will be deleted, if `No` the user will be prompted to specify an alternate folder.
- If the selected folder does not exist, it will be created.
- The contents of the `reference mockup` shall be copied into the `new mockup` folder.
- For each `AutomationNode` resource that exists in the new mockup tree: Remove the `Chassis` resource associated with it.  The `Chassis` resource can be found from the `AutomationNode` resource's Links->Chassis navigation link.  When removing the `Chassis` object, its subfolder from the Chassis collection shall be removed and the `ChassisCollection` shall be updated.  In addition, any links to the removed `Chassis` resource within the entire resource tree shall be removed.
 - For each `AutomationNode` resource that exists in the `new mockup` tree: Remove the AutomationNode's associated folder, update the AutomationNode collection, and remove any links to the `AutomationNode` resource that may exist elsewhere in the `new mockup` resource tree.
 - For any `Cable` resources with no Links->DownstreamChassis reference and include the text "AutomationNode" in the name, remove the cable and update the CableCollection.  Remove any links to the cable resource that may be found elsewhere in the `new mockup` resource tree.
 - For any `USBController` resource with an ID of `AutomationUsb`, delete the resource's folder within the resource tree and remove any links to the resource from the `new mockup` resource tree.

# Step 2 - Preparation
- If only one `System` resource exists in the top-level `Systems` collection, that system shall be selected as the `automation_system`
- If more than one `System` resource exists in the top-level System collection, the user shall be prompted to select the `automation_system` from a list of the existing `System` resources.
- If no `System` resources exist within the top-level `Systems` collection, or no top-level `Systems` collection exists.  Report the error and allow the user to specify a different `reference mockup` or exit.
- If only one `Manager` resource exists in the top-level `Managers` collection, that `Manager` shall be selected as the automation manager system: `automation_manager`
- If more than one Manager exists in the top-level Managers collection, the user shall be prompted to select the automation manager: `automation_manager`
- If no `Manager` resource exists within the top-level `Managers` collection, or no top-level `Managers` collection exists.  Report the error and allow the user to specify a different `reference mockup` or exit.
- If no top-level `Cables` collection exists, one shall be created.
- When creating a cable collection, the collection shall be of type: `#CableCollection.CableCollection`,
- When creating a cable collection, the collection's `Members` list shall be empty.
- If no top-level `AutomationNodes` collection exists, one shall be created.
- When creating am `AutomationNodes` collection, the collection shall be of type: `#AutomationNodeCollection.AutomationNodeCollection`,
- When creating an `AutomationNodes` collection, the collection's `Members` list shall be empty.

# Step 3 - Resource Generation
This section documents the process of creating IoT.1/IoT.2-related resources within the `new mockup` resource tree.  Resources are added one endpoint at a time in the order documented in each of the sub-steps in this section.  Throughout this section `pdrs` should be interpreted as the collection of pdr records associated with the endpoint and found within the `pdr_file`.  `fru info` refers to the fru records or fru data within `pdr_file` that is associated with the endpoint.

## Step 3.1 gather endpoint information from user
-find the `entityIDName` value within the `entityNames` field within the `OEM Entity ID PDR` in `pdrs`.  If `entityIDName` cannot be found, or if more than one can be found - exit with an error. 
- Display the following information about the endpoint, if it exists:
1. the device path (top-level `dev` field in the endpoint data in `pdr_file`) that the endpoint is connected to (e.g. /dev/ttyUSB0)
2. the `entityIDName` value
3. The device `Model` (from `fru info`)
4. The device `Serial Number` (from fru data)
- Prompt the user to enter a `short_name` for the device (e.g. XMover)
- Prompt the user to type a `short_description` of the function of the endpoint "Controller to move print head on the x axis"

## Step 3.2 create an AutomationNode resource
Create an `AutomationNode` resource for the endpoint.  The `resource_id` of the node shall be based on the short name given by the user with the following changes: space characters are converted to underscore characters.  If the name has already been used for another resource, append an underscore followed by a unique number to the resource name.  For the first duplicate resource, the number will be _2. For the second duplicate resource, the number will be _3.  Each additional duplicate will increment the number by one.  The `resource_id` shall be lower-case.

The `AutomationNode` resource should be added to the top-level `AutomationNodes` collection.

Below is the template `AutomationNode`.  Double triangular braces identify areas were programatic replacement should be done. Instructions for how to perform the replacement can be found within the double triangular braces. Once replacement is completed, the braces (and any text they contain) should be removed.

```json
{
    "@odata.type": "#AutomationNode.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.AutomationNode",
	"Id": "<<resource_id>>",
    "Name": "<<short_name>>",
	"Description": "<<short_description>>",
	"Actions": {
        "@odata.type": "#AutomationNode.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Actions",
		"#AutomationNode.Reset": {
			"target": "/redfish/v1/AutomationNodes/<<resource_id>>/Actions/AutomationNode.Reset"
		},
		"#AutomationNode.SendTrigger": {
			"target": "/redfish/v1/AutomationNodes/<<resource_id>>/Actions/AutomationNode.SendTrigger"
		},
        <<Include this Action If entityIDName is PID or Profiled>>
		"#AutomationNode.Start": {
			"target": "/redfish/v1/AutomationNodes/<<resource_id>>/Actions/AutomationNode.Start"
		},
        <<Include this Action If entityIdName is a PID or Profiled>>
		"#AutomationNode.Stop": {
			"target": "/redfish/v1/AutomationNodes/<<resource_id>>/Actions/AutomationNode.Stop"
		},
        <<Include this Action If entityIdName is Profiled>>
		"#AutomationNode.Wait": {
			"target": "/redfish/v1/AutomationNodes/<<resource_id>>/Actions/AutomationNode.Wait"
		},
		"Oem": {}
	},
	"Links": {
		"Chassis": [
			{
				"@odata.id" : "/redfish/v1/Chassis/<<resource_id>>"
			}
		],
        <<Include OutputControl only if entityIdName is a PID or Profiled>>
        "OutputControl": {
            "@odata.id" : "/redfish/v1/Chassis/<<resource_id>>/Controls/EFFECTER_ID_4"
        },
        <<Include PidFeedbackSensor only entityIdName is a PID>>
        "PidFeedbackSensor": {
			"@odata.id" : "/redfish/v1/Chassis/<<resource_id>>/Sensors/SENSOR_ID_5"
        },
        <<Include PositionSensor only if the entityIdName is Profiled, and Numeric Sensor PDR with SensorID 7 exists in pdrs>>
		"PositionSensor": {
			"@odata.id" : "/redfish/v1/Chassis/<<resource_id>>/Sensors/SENSOR_ID_7"
		}
	},
	"Instrumentation": {
        "@odata.id": "/redfish/v1/AutomationNodes/<<resource_id>>/AutomationInstrumentation"
    },
	"NodeType": "<<PID if entityIDName is PID, Simple if entityIDName is Simple, otherwise MotionPosition>>",
	"NodeState": "Idle",
	"Status": {
        "State": "Enabled",
        "Health": "OK"
	},
    "@odata.context": "/redfish/v1/$metadata#AutomationNode.AutomationNode",
	"@odata.id": "/redfish/v1/AutomationNodes/<<resource_id>>"
}
```

## Step 3.3 create a Chassis resource
Create a `Chassis` resource for the endpoint.  The `resource_id` of the `Chassis` resource should match the name of the `AutomationNode` resource (`short_name`).

The `Chassis` resource should be added to the top-level `Chassis` collection.

Below is the template `Chassis` resource.  Double triangular braces identify areas were programatic replacement should be done. Instructions for how to perform the replacement can be found within the double triangular braces. Once replacement is completed, the braces (and any text they contain) should be removed.
```json
{
    "@odata.type": "#Chassis.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Chassis",
    "Id": "<<resource_id>>",
    "Name" : "Chassis resource for <<short_description>>",
    "ChassisType": "Module",
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    "AssetTag": "<<the value of the Asset Tag field within the fru info if it exists, otherwise do not include this field>>",
    "DateOfManufacture": "<<the value of the Manufacture Date field within the fru info if it exists, otherwise do not include this field>>",
    "SerialNumber": "<<the value of the Serial Number field within the fru info if it exists, otherwise do not include this field>>",
    "Manufacturer": "<<the value of the Manufacturer field within the fru info if it exists, otherwise do not include this field>>",
    "Model": "<<the value of the Model field within the fru info if it exists, otherwise do not include this field>>",
    "PartNumber": "<<the value of the Part Number field within the fru info if it exists, otherwise do not include this field>>",
    "SKU": "<<the value of the SKU field within the fru info if it exists, otherwise do not include this field>>",
    "Version": "<<the value of the Version field within the fru info if it exists, otherwise do not include this field>>",
    <<only include the Sensors field if the endpoint has Numeric Sensor PDRs in its pdrs>>
    "Sensors" : {
        "@odata.id": "/redfish/v1/Chassis/<<resource_id>>/Sensors"
    },
    <<only include the Controls field if the endpoint has Numeric Effecter PDRs  in its pdrs>>
    "Controls" : {
        "@odata.id": "/redfish/v1/Chassis/<<resource_id>>/Controls"
    },
    <<only include the Assembly field if there is fru data associated with the endpoint>>
    "Assembly" : {
        "@odata.id": "/redfish/v1/Chassis/<<resource_id>>/Assembly"
    },
    "Links": {
        "ManagedBy": [
            {
                "@odata.id": "/redfish/v1/Managers/<<automation_manager>>"
            }
        ],
        "AutomationNodes": [
            {
                "@odata.id": "/redfish/v1/AutomationNodes/<<resource_id>>"
            }
        ]
    },
    "@odata.context": "/redfish/v1/$metadata#Chassis.Chassis",
    "@odata.id": "/redfish/v1/Chassis/<<resource_id>>"
}
```
### Step 3.3.1 Numeric Sensor Resources
`Sensor` resources are created as members of the associated `Chassis` `Sensors` collection.  Sensor `sensor_id` values shall follow the naming convention `SENSOR_ID_<n>` where `<n>` is sensorId value in the associated Numeric Sensor PDR (`sensor_pdr`) in `pdrs`.

The following data may be useful in constructing `Sensor` resources. The lookup condition for the SENSOR_DATA Table is the combined (`sensor_id`, `entityIDName`) pair. *ANY* is a wildcard that means any value of `entityIDName` will match the condition. Other columns give data values that will be used to fill out the template Sensor resource structure below when the condition is met. For every Numeric Sensor PDR that meets the conditions in the table, a `Sensor` resource must be createed, otherwise, no. 

**SENSOR_DATA Table**
| `sensor_id` | `entityIDName` | Function |
|---|---|---| 
| SENSOR_ID_1  | *Any* | Global Interlock |
| SENSOR_ID_2  | *Any* | Trigger |
| SENSOR_ID_3 - SENSOR_ID_255 | Simple | General Sensor |   
| SENSOR_ID_4  | PID | Control Error |
| SENSOR_ID_5  | PID | Feedback |
| SENSOR_ID_4  | Position | Velocity Error | 
| SENSOR_ID_5  | Position | Position Error |
| SENSOR_ID_6  | Position | Velocity |
| SENSOR_ID_7  | Position | Position |
| SENSOR_ID_8  | Position | Positive Limit |
| SENSOR_ID_9  | Position | Negative Limit |

The `Sensor` resource shall be created at `redfish/v1/Chassis/<<resource_id>>/Sensors/<<sensor_id>>/index.json`.  The Chassis `Sensors` collection at `redfish/v1/Chassis/<<resource_id>>/Sensors/index.json` must be updated by appending the `Sensor` resource's `@odata.id` to the collection's `Members[]` and incrementing `Members@odata.count`.

Fill placeholders marked by `<<...>>` programmatically and remove the triangular braces in the final output.

There exists a python function that converts pldm-coded units fields into a ucum-compliant units string for the resource's units field.  Use pdr_units_to_ucum.py to make the units conversion.

Throughout this section `sensor_pdr` refers to the Numeric Sensor PDR object for the endpoint as found in the `pdr_file`. `sensor_pdr` contains a top-level `decoded` object; all `sensor_pdr` keywords in this section can be found within `decoded`. These referenced values are always expected to be present with numeric types.

```json
{
    "@odata.type": "#Sensor.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Sensor",
  "@odata.context": "/redfish/v1/$metadata#Sensor.Sensor",
  "@odata.id": "/redfish/v1/Chassis/<<resource_id>>/Sensors/<<sensor_id>>",
  "Id": "<<sensor_id>>",
  "Name": "<<function from SENSOR_DATA Table (above) for appropriate sensor_id and entityIDName>> for <<short_name>>",
  "Description": "<<function from SENSOR_DATA Table (above) for appropriate sensor_id and entityIDName>> for <<short_name>>",
  "Reading": null,
  "ReadingUnits": "<<convert from sensor_pdr fields using pdr_units_to_ucum function>>",
  "ReadingAccuracy": <<compute from sensor_pdr fields as shown:  plusTolerance + maxReadable*accuracy/100 >>,
  "ReadingRangeMax": <<from sensor_pdr fields: maxReadable>>,
  "ReadingRangeMin": <<from sensor_pdr fields: minReadable>>,
  "SensingInterval": <<from sensor_pdr field: updateInterval>>,
  "Status": {
    "State": "Enabled",
    "Health": "OK"
  },
    <<If the sensor_pdr has the bitfield supportedThresholds <> 0, include the following field>>
    "Thresholds": {
        <<If the sensor_pdr supportedThresholdsFlags->LowerThresholdWarning is true, include the following field>>
        "LowerCaution": {
            "Reading": <<value from sensor_pdr for warningLow>>,
            "Activation": "Disabled",
            "HysteresisReading": <<compute from the sensor_pdr values: hysteresis>>
        },
        <<If the sensor_pdr supportedThresholdsFlags->LowerThresholdCritical is true, include the following field>>
        "LowerCritical": {
            "Reading": <<value from sensor_pdr for criticalLow>>,
            "Activation": "Disabled",
            "HysteresisReading": <<compute from the sensor_pdr values: hysteresis>>
        },
        <<If the sensor_pdr supportedThresholdsFlags->LowerThresholdFatal is true, include the following field>>
        "LowerFatal": {
                "Reading": <<value from sensor_pdr for fatalLow>>,
                "Activation": "Disabled",
                "HysteresisReading": <<compute from the sensor_pdr values: hysteresis>>
        },
        <<If sensor_pdr supportedThresholdsFlags->UpperThresholdWarning is true, include the following field>>
        "UpperCaution": {
                "Reading": <<value from sensor_pdr for warningHigh>>,
                "Activation": "Disabled",
                "HysteresisReading": <<compute from the sensor_pdr values: hysteresis>>
        },
        <<If sensor_pdr supportedThresholdsFlags->UpperThresholdCritical is true, include the following field>>
        "UpperCritical": {
                "Reading": <<value from sensor_pdr for criticalHigh>>,
                "Activation": "Disabled",
                "HysteresisReading": <<compute from the sensor_pdr values: hysteresis>>
        },
        <<If sensor_pdr supportedThresholdsFlags->UpperThresholdFatal is true, include the following field>>
        "UpperFatal": {
                "Reading": <<value from sensor_pdr for fatalHigh>>,
                "Activation": "Disabled",
                "HysteresisReading": <<compute from the sensor_pdr values: hysteresis>>
        }
    },
    "Links": {
    "Chassis": {
      "@odata.id": "/redfish/v1/Chassis/<<resource_id>>"
    }
  }
}
```
### Step 3.3.2 Numeric Effecter (Control) Resources
`Control` resources are created as members of the associated `Chassis` `Controls` collection.  Control `control_id` values shall follow the naming convention `EFFECTER_ID_<n>` where `<n>` is the effecterId value in the associated Numeric Effecter PDR (`effecter_pdr`) in `pdrs`.

The following data may be useful in constructing `Control` resources. The lookup condition for the CONTROL_DATA Table is the combined (`control_id`,`entityIDName`) pair.  *ANY* is a wildcard that means any value of `entityIDName` will match the condition.  Other columns give data values that will be used to fill out the template `Control` resource structure below when the condition is met. For every Numeric Effecter PDR that meets the condition in the table, a `Control` resource must be created, otherwise, no. 

**CONTROL_DATA Table**
| `control_id` | `entityIDName` | Function | Referenced `sensor_id` |
|---|---|---|---|
| EFFECTER_ID_1  | *Any* | Global Interlock | SENSOR_ID_1 | 
| EFFECTER_ID_2  | *Any* | Trigger | SENSOR_ID_2 |
| EFFECTER_ID_3 - EFFECTER_ID_255 | Simple | General Effecter |   
| EFFECTER_ID_4  | PID | SetPoint | SENSOR_ID_5 |
| EFFECTER_ID_4  | Position | Position | SENSOR_ID_7 | 
| EFFECTER_ID_5  | Position | Velocity Profile |
| EFFECTER_ID_6  | Position | Acceleration Profile |
| EFFECTER_ID_7  | Position | Acceleration Gain |

The `Control` resource shall be created at `redfish/v1/Chassis/<<resource_id>>/Controls/<<control_id>>/index.json`.  The Chassis `Controls` collection at `redfish/v1/Chassis/<<resource_id>>/Controls/index.json` must be updated by appending the `Control` resource's `@odata.id` to the collection's `Members[]` and incrementing `Members@odata.count`.

Fill placeholders marked by `<<...>>` programmatically and remove the triangular braces in the final output.

There exists a python function that converts pldm-coded units fields into a ucum-compliant units string for the resource's units field.  Use pdr_units_to_ucum.py to make the units conversion.

Throughout this section `effecter_pdr` refers to the Numeric Effecter PDR object for the endpoint as found in the `pdr_file`. `effecter_pdr` contains a top-level `decoded` object; all `effecter_pdr` keywords in this section can be found within `decoded`.  These referenced values are always expected to be present with numeric types.

```json
{
    "@odata.type": "#Control.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Control",
    "Id": "<<control_id>>",
    "Name": "<<function from CONTROL_DATA Table (above) for appropriate control_id and entityIDName>> for <<short_name>>",
    "Description":"<<function from CONTROL_DATA Table (above) for appropriate control_id and entityIDName>> for <<short_name>>",
    "SetPointType": "Single",
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    "ControlMode": "Manual",
    "SetPoint": null,
    "SetPointUnits": "<<convert from pldm fields using pdr_units_to_ucum function>>",
    "AllowableMax": <<value of maxSettable from effecter_pdr>>,
    "AllowableMin": <<value of minSettable from effecter_pdr>>,
    "SettingMax": <<value of maxSettable from effecter_pdr>>,
    "SettingMin": <<value of minSettable from effecter_pdr>>,
    "Implementation": "Programmable",
    <<include this field only if "Referenced `sensor_id`" is specified in EFFECTER_DATA Table above>>
    "Sensor": {
        "Reading": <<value of this field from the sensor within the same chassis with the referenced `sensor_id`>>,
        "DataSourceUri": "/redfish/v1/Chassis/<<resource_id>>/Sensors/<<Referenced `sensor_id`>>"
    },
    <<include the following field only if the entityIDName is PID and this `control_id` corresponds to EFFECTER_ID_4 >>
    "ControlLoop": {
        "Proportional": 0,
        "Integral": 0,
        "Differential": 0
    },
    "@odata.context": "/redfish/v1/$metadata#Control.Control",
    "@odata.id": "/redfish/v1/Chassis/<<resource_id>>/Controls/<<control_id>>"
}
```

## 3.4 Create AutomationInstrumentation resource 
the AutomationInstrumentation node resource should be placed in a subfoler of its associated AutomationNode at /redfish/v1/AutomationNodes/<<resource_id>>/AutomationInstrumentation. Specific contents of this resource will depend upon the PDR settings and are detailed below.

Fill placeholders marked by `<<...>>` programmatically and remove the triangular braces in the final output.

```json
{
    "@odata.type": "#AutomationInstrumentation.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.AutomationInstrumentation",
    "@odata.context": "/redfish/v1/$metadata#AutomationInstrumentation.AutomationInstrumentation",
    "@odata.id": "/redfish/v1/AutomationNodes/<<resource_id>>/AutomationInstrumentation",
    "Id": "AutomationInstrumentation",
    "Name": "Instrumentation for <<short_name>> AutomationNode",
    "NodeState": "<<When entityIDName is Simple value is Running, otherwise value is Idle>>",
    "Status": {
        "State": "Enabled",
        "Health": "OK"
    },
    <<If Links->OutputControl exists in the AutomationNode at /redfish/v1/AutomationNodes/<<resource_id>>, and entityIDName is not PID, this field will be present, otherwise, no>>
    "NodeControl": {
        <<All field values in this object shall come directly from the Control resource pointed to by the Links->OutputControl navigation link in AutomationNode at /redfish/v1/AutomationNodes/<<resource_id>>.  If a specific field does not exist in the Links->OutputControl, do not include it here.>>
        "SetPoint": <<see note above.>>,
        "SetPointUnits": <<see note above>>,
        "AllowableMin": <<see note above>>,
        "AllowableMax": <<see note above>>,
        "DataSourceUri": "/redfish/v1/Chassis/<<resource_id>>/Controls/EFFECTER_ID_4"
    },
    <<If Links->OutputControl exists in the AutomationNode at /redfish/v1/AutomationNodes/<<resource_id>>, and entityIDName is PID, this field will be present, otherwise, no>>
    "PID": {
        <<All field values in this object shall come directly from the Control resource pointed to by the Links->OutputControl navigation link in AutomationNode at /redfish/v1/AutomationNodes/<<resource_id>>.  If a specific field does not exist in the source resource, do not include it here.>>
        "SetPoint": <<see note above>>,
        "SetPointUnits": <<see note above>>,
        "Feedback": <<see note above>>,
        "Error": <<see note above>>,
        "LoopParameters": <<see note above>>,
        <<this value should match the URI contained in the OutputControl navigation link in the AutomationNode that references this resource.>>
        "DataSourceUri": "/redfish/v1/Chassis/<<resource_id>>/Controls/EFFECTER_ID_4"
    },
    "Actions": {
        "Oem": {}
    }
}
```

## 3.5 Create Assembly resource 
the `Assembly` resource should be placed in a subfoler of its associated Chassis at /redfish/v1/Chassis/<<resource_id>>/Assembly. Specific contents of this resource will depend upon the `fru info` settings and are detailed below.

Fill placeholders marked by `<<...>>` programmatically and remove the triangular braces in the final output.

```json
{
    "@odata.type": "#Assembly.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Assembly",
    "Id": "Assembly",
    "Name": "Assembly",
    "Description": "Assembly for <<short_name>>",
    "Assemblies": [
        {
            "Description": "raw FRU data from AutomationNode",
            "EngineeringChangeLevel": "<<the value of the Engineering Change Level field within the `fru info` if it exists, otherwise do not include this field>>",
            "Model": "<<the value of the Model field within the `fru info` if it exists, otherwise do not include this field>>",
            "PartNumber": "<<the value of the Part Number field within the `fru info` if it exists, otherwise do not include this field>>",
            "Producer": "<<the value of the Manufacturer field within the `fru info` if it exists, otherwise do not include this field>>",
            "ProductionDate": "<<the value of the Manufacture Date field within the `fru info` if it exists, otherwise do not include this field>>",
            "SKU": "<<the value of the SKU field within the `fru info` if it exists, otherwise do not include this field>>",
            "SerialNumber": "<<the value of the Serial Number field within the `fru info` if it exists, otherwise do not include this field>>",
            "Vendor": "<<the value of the Vendor field within the `fru info` if it exists, otherwise do not include this field>>",
            "Version": "<<the value of the Version field within the `fru info` if it exists, otherwise do not include this field>>",
            "BinaryDataURI": "<<The value of the raw_fru_data from the `fru info`>>"
        }
    ],
    "@odata.context": "/redfish/v1/$metadata#Assembly.Assembly",
    "@odata.id": "/redfish/v1/Chassis/<<resource_id>>/Assembly"
}
```

## 3.6 Cables
For every endpoint object that exists in `pdr file`, a cable will be added if the `pdr file` contains a usb_addr field for the endpoint.

**Creating a usb controller collection in the system resource**
if no usb controller collection can be found for the `automation_system`, one will be created in accordance with the redfish schema by adding the following field to the `automation_system` resource's navigation links (Links) list:

```json
"USBControllers": {
    "@odata.id": "/redfish/v1/Systems/<<automation_system>>/USBControllers"
}
```

if no USB controller collection resource exists, a USB controller collection shall be placed at the resource location redfish/v1/Systems/<<automation_system>>/USBControllers. Its structure should be:

```json
{
    "@odata.type": "#USBControllerCollection.USBControllerCollection",
    "Name": "USBControllers",
    "Description": "USB Controllers",
    "Members@odata.count": 1,
    "Members": [
        {
            "@odata.id": "/redfish/v1/Systems/<<automation_system>>/USBControllers/USB1"
        }
    ],
    "@odata.id": "/redfish/v1/Systems/<<automation_system>>/USBControllers"
}
```

**adding a usb controller**
The usb controller shall be created at redfish/v1/Systems/<<automation_system>>/USBControllers/AutomationUsb and shall have a form of:
```json
{
    "@odata.type": "#USBController.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.USBController",
    "Id": "USB1",
    "Name": "Automation USB Controller",
    "Ports": {
    },
    "@odata.context": "/redfish/v1/$metadata#USBController.USBController",
    "@odata.id": "/redfish/v1/Systems/<<automation_system>>/USBControllers/AutomationUsb"
}
```

**adding cables to the system**
Create a port resource locator in the AutomationUsb resource's Ports collection.  Then create a port which is stored at that resource location.

Note <<port_id>> is a unique numeric identifier formed by incrementing a count value for each port added.  port_id has a starting value of 1.

The new port should have this form:
```json
{
    "@odata.type": "#Port.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Port",
    "Id": "<<port_id>>",
    "Name": "USB Port <<port_id>>",
    "Description": "Automation USB Port <<port_id>>",
    "PortId": "<<usb_identifier value from endpoint data in `pdr file`>>",
    "Location": {
        "PartLocation": {
            "ServiceLabel": "unspecified",
            "LocationOrdinalValue": 1,
            "LocationType": "Connector"
        }
    },
    "@odata.context": "/redfish/v1/$metadata#Port.Port",
    "@odata.id": "/redfish/v1/Systems/<<aggregation_system>>/USBControllers/AutomationUsb/Ports/<<port_id>>"
}
```
In the system's Cables Collection, create a new cable with the following from.
Note `cable_id` is the string "node_cable_" followed by a unique numeric identifier formed by incrementing a count value for each port added.  `cable_id` has a starting value of 1.

```json
{
  "@odata.type": "#Cable.<<Extract most recent schema version from new mockup /redfish/v1/$metadata/index.xml (e.g. v1_27_0)>>.Cable",
  "Id": "<<cable_id>>",
  "Name": "AutomationNode cable for <<resource_id>>",
  "Links": {
    "UpstreamChassis": [
      {
        "@odata.id": "/redfish/v1/Chassis/<<chassis resource associated with automation_system>>"
      }
    ],
    "UpstreamPorts": [
      {
        "@odata.id": "/redfish/v1/Systems/<<automation_system>>/USBControllers/AutomationUsb/Ports/<<port_id>>"
      }
    ],
    "DownstreamChassis": [
      {
        "@odata.id": "/redfish/v1/Chassis/<<resource_id>>"
      }
    ]
  },
  "@odata.context": "/redfish/v1/$metadata#Cable.Cable",
  "@odata.id": "/redfish/v1/Cables/<<cable_id>>"
}
```
