#include "sensor.h"
#include <iostream>
#include <chrono>

namespace iot1::sensor {

// Base Sensor
Sensor::Sensor(uint16_t id, const std::string& name)
    : sensorId(id), name(name), initialized(false) {}

// NumericSensor
NumericSensor::NumericSensor(uint16_t id, const std::string& name)
    : Sensor(id, name), minValue(0.0f), maxValue(100.0f), 
      resolution(0.1f), tolerance(0.0f), units("") {}

json NumericSensor::readValue() const {
    json value = {
        {"sensorId", sensorId},
        {"type", "Numeric"},
        {"value", 50.0f},  // Placeholder
        {"units", units},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
    return value;
}

bool NumericSensor::initialize(const json& config) {
    try {
        if (config.contains("minValue")) minValue = config["minValue"];
        if (config.contains("maxValue")) maxValue = config["maxValue"];
        if (config.contains("resolution")) resolution = config["resolution"];
        if (config.contains("units")) units = config["units"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize NumericSensor: " << e.what() << std::endl;
        return false;
    }
}

bool NumericSensor::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR NumericSensor::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x08);  // Numeric Sensor PDR type
    pdr.setSensorId(sensorId);
    pdr.setEntityType(0x6000);  // OEM entity
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    // Add numeric-specific fields
    pdr["minValue"] = minValue;
    pdr["maxValue"] = maxValue;
    pdr["resolution"] = resolution;
    pdr["units"] = units;
    
    return pdr;
}

// StateSensor
StateSensor::StateSensor(uint16_t id, const std::string& name)
    : Sensor(id, name), stateSetId(0) {}

json StateSensor::readValue() const {
    json value = {
        {"sensorId", sensorId},
        {"type", "State"},
        {"state", 0},  // Placeholder
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
    return value;
}

bool StateSensor::initialize(const json& config) {
    try {
        if (config.contains("possibleStates")) {
            possibleStates = config["possibleStates"].get<std::vector<std::string>>();
        }
        if (config.contains("stateSetId")) stateSetId = config["stateSetId"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize StateSensor: " << e.what() << std::endl;
        return false;
    }
}

bool StateSensor::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR StateSensor::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x04);  // State Sensor PDR type
    pdr.setSensorId(sensorId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["stateSetId"] = stateSetId;
    pdr["possibleStateCount"] = static_cast<int>(possibleStates.size());
    
    json states = json::array();
    for (const auto& state : possibleStates) {
        states.push_back(state);
    }
    pdr["possibleStates"] = states;
    
    return pdr;
}

void StateSensor::setPossibleStates(const std::vector<std::string>& states) {
    possibleStates = states;
}

// BooleanSensor
BooleanSensor::BooleanSensor(uint16_t id, const std::string& name)
    : Sensor(id, name), trueLabel("On"), falseLabel("Off") {}

json BooleanSensor::readValue() const {
    json value = {
        {"sensorId", sensorId},
        {"type", "Boolean"},
        {"value", false},  // Placeholder
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
    return value;
}

bool BooleanSensor::initialize(const json& config) {
    try {
        if (config.contains("trueLabel")) trueLabel = config["trueLabel"];
        if (config.contains("falseLabel")) falseLabel = config["falseLabel"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize BooleanSensor: " << e.what() << std::endl;
        return false;
    }
}

bool BooleanSensor::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR BooleanSensor::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x04);  // State Sensor PDR type
    pdr.setSensorId(sensorId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["stateSetId"] = 0;  // Boolean state set
    pdr["possibleStates"] = json::array({trueLabel, falseLabel});
    
    return pdr;
}

// RateSensor
RateSensor::RateSensor(uint16_t id, const std::string& name)
    : Sensor(id, name), minRate(0.0f), maxRate(1000.0f), rateUnit("Hz") {}

json RateSensor::readValue() const {
    json value = {
        {"sensorId", sensorId},
        {"type", "Rate"},
        {"rate", 0.0f},  // Placeholder
        {"unit", rateUnit},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
    return value;
}

bool RateSensor::initialize(const json& config) {
    try {
        if (config.contains("minRate")) minRate = config["minRate"];
        if (config.contains("maxRate")) maxRate = config["maxRate"];
        if (config.contains("rateUnit")) rateUnit = config["rateUnit"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize RateSensor: " << e.what() << std::endl;
        return false;
    }
}

bool RateSensor::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR RateSensor::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x08);  // Numeric Sensor PDR type
    pdr.setSensorId(sensorId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["minRate"] = minRate;
    pdr["maxRate"] = maxRate;
    pdr["rateUnit"] = rateUnit;
    
    return pdr;
}

// QuadratureEncoderSensor
QuadratureEncoderSensor::QuadratureEncoderSensor(uint16_t id, const std::string& name)
    : Sensor(id, name), countsPerRevolution(360.0f), supportsDirection(true) {}

json QuadratureEncoderSensor::readValue() const {
    json value = {
        {"sensorId", sensorId},
        {"type", "QuadratureEncoder"},
        {"position", 0.0f},  // Placeholder
        {"velocity", 0.0f},
        {"direction", 0},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
    return value;
}

bool QuadratureEncoderSensor::initialize(const json& config) {
    try {
        if (config.contains("countsPerRevolution")) countsPerRevolution = config["countsPerRevolution"];
        if (config.contains("supportsDirection")) supportsDirection = config["supportsDirection"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize QuadratureEncoderSensor: " << e.what() << std::endl;
        return false;
    }
}

bool QuadratureEncoderSensor::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR QuadratureEncoderSensor::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x08);  // Numeric Sensor PDR type
    pdr.setSensorId(sensorId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["countsPerRevolution"] = countsPerRevolution;
    pdr["supportsDirection"] = supportsDirection;
    pdr["type"] = "QuadratureEncoder";
    
    return pdr;
}

} // namespace iot1::sensor
