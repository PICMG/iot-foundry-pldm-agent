#include "iot1/endpoint/endpoint.h"
#include <iostream>

namespace iot1::endpoint {

// Base Endpoint
Endpoint::Endpoint(uint16_t eid, const std::string& name)
    : eid(eid), name(name), initialized(false) {}

// SimpleEndpoint
SimpleEndpoint::SimpleEndpoint(uint16_t eid, const std::string& name)
    : Endpoint(eid, name) {}

bool SimpleEndpoint::initialize(const json& config) {
    try {
        // Load simple endpoint configuration
        if (config.contains("sensors")) {
            // Process sensors configuration
        }
        if (config.contains("effecters")) {
            // Process effecters configuration
        }
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize SimpleEndpoint: " << e.what() << std::endl;
        return false;
    }
}

bool SimpleEndpoint::shutdown() {
    initialized = false;
    return true;
}

json SimpleEndpoint::getCapabilities() const {
    json caps = {
        {"type", "Simple"},
        {"maxSensors", 16},
        {"maxEffecters", 16},
        {"supportsGlobalInterlock", false}
    };
    return caps;
}

json SimpleEndpoint::getStatus() const {
    json status = {
        {"eid", eid},
        {"name", name},
        {"type", "Simple"},
        {"initialized", initialized}
    };
    return status;
}

// PidControlEndpoint
PidControlEndpoint::PidControlEndpoint(uint16_t eid, const std::string& name)
    : Endpoint(eid, name), proportionalGain(1.0f), integralGain(0.0f), 
      derivativeGain(0.0f), setpoint(0.0f), outputLimit(100.0f) {}

bool PidControlEndpoint::initialize(const json& config) {
    try {
        if (config.contains("pid")) {
            const auto& pidConfig = config["pid"];
            if (pidConfig.contains("kp")) proportionalGain = pidConfig["kp"];
            if (pidConfig.contains("ki")) integralGain = pidConfig["ki"];
            if (pidConfig.contains("kd")) derivativeGain = pidConfig["kd"];
            if (pidConfig.contains("outputLimit")) outputLimit = pidConfig["outputLimit"];
        }
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize PidControlEndpoint: " << e.what() << std::endl;
        return false;
    }
}

bool PidControlEndpoint::shutdown() {
    initialized = false;
    return true;
}

json PidControlEndpoint::getCapabilities() const {
    json caps = {
        {"type", "PID"},
        {"supportsGlobalInterlock", true},
        {"supportsTrigger", true},
        {"outputTypes", json::array({"analog", "digital"})}
    };
    return caps;
}

json PidControlEndpoint::getStatus() const {
    json status = {
        {"eid", eid},
        {"name", name},
        {"type", "PID"},
        {"initialized", initialized},
        {"pid", {
            {"kp", proportionalGain},
            {"ki", integralGain},
            {"kd", derivativeGain},
            {"setpoint", setpoint},
            {"outputLimit", outputLimit}
        }}
    };
    return status;
}

void PidControlEndpoint::setGains(float kp, float ki, float kd) {
    proportionalGain = kp;
    integralGain = ki;
    derivativeGain = kd;
}

void PidControlEndpoint::setSetpoint(float sp) {
    setpoint = sp;
}

// ProfiledMotionControlEndpoint
ProfiledMotionControlEndpoint::ProfiledMotionControlEndpoint(uint16_t eid, const std::string& name)
    : Endpoint(eid, name), acceleration(1.0f), velocity(1.0f), 
      deceleration(1.0f), positionSetpoint(0.0f) {}

bool ProfiledMotionControlEndpoint::initialize(const json& config) {
    try {
        if (config.contains("motion")) {
            const auto& motionConfig = config["motion"];
            if (motionConfig.contains("acceleration")) acceleration = motionConfig["acceleration"];
            if (motionConfig.contains("velocity")) velocity = motionConfig["velocity"];
            if (motionConfig.contains("deceleration")) deceleration = motionConfig["deceleration"];
        }
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize ProfiledMotionControlEndpoint: " << e.what() << std::endl;
        return false;
    }
}

bool ProfiledMotionControlEndpoint::shutdown() {
    initialized = false;
    return true;
}

json ProfiledMotionControlEndpoint::getCapabilities() const {
    json caps = {
        {"type", "ProfiledMotion"},
        {"supportsTrapezoidal", true},
        {"supportsLinear", true},
        {"supportsGlobalInterlock", true},
        {"maxPosition", 360.0f}
    };
    return caps;
}

json ProfiledMotionControlEndpoint::getStatus() const {
    json status = {
        {"eid", eid},
        {"name", name},
        {"type", "ProfiledMotion"},
        {"initialized", initialized},
        {"motion", {
            {"acceleration", acceleration},
            {"velocity", velocity},
            {"deceleration", deceleration},
            {"positionSetpoint", positionSetpoint}
        }}
    };
    return status;
}

void ProfiledMotionControlEndpoint::setProfile(float accel, float vel, float decel) {
    acceleration = accel;
    velocity = vel;
    deceleration = decel;
}

void ProfiledMotionControlEndpoint::setPosition(float pos) {
    positionSetpoint = pos;
}

// CompositeEndpoint
CompositeEndpoint::CompositeEndpoint(uint16_t eid, const std::string& name)
    : Endpoint(eid, name) {}

bool CompositeEndpoint::initialize(const json& config) {
    try {
        // Initialize all child endpoints
        for (auto& child : childEndpoints) {
            if (!child->initialize(config)) {
                return false;
            }
        }
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize CompositeEndpoint: " << e.what() << std::endl;
        return false;
    }
}

bool CompositeEndpoint::shutdown() {
    for (auto& child : childEndpoints) {
        child->shutdown();
    }
    initialized = false;
    return true;
}

json CompositeEndpoint::getCapabilities() const {
    json caps = {
        {"type", "Composite"},
        {"childCount", childEndpoints.size()},
        {"children", json::array()}
    };
    
    for (const auto& child : childEndpoints) {
        caps["children"].push_back(child->getCapabilities());
    }
    
    return caps;
}

json CompositeEndpoint::getStatus() const {
    json status = {
        {"eid", eid},
        {"name", name},
        {"type", "Composite"},
        {"initialized", initialized},
        {"childCount", childEndpoints.size()},
        {"children", json::array()}
    };
    
    for (const auto& child : childEndpoints) {
        status["children"].push_back(child->getStatus());
    }
    
    return status;
}

void CompositeEndpoint::addChild(std::shared_ptr<Endpoint> endpoint) {
    if (endpoint) {
        childEndpoints.push_back(endpoint);
    }
}

void CompositeEndpoint::removeChild(uint16_t eid) {
    childEndpoints.erase(
        std::remove_if(childEndpoints.begin(), childEndpoints.end(),
                      [eid](const std::shared_ptr<Endpoint>& ep) { return ep->getEid() == eid; }),
        childEndpoints.end()
    );
}

std::shared_ptr<Endpoint> CompositeEndpoint::getChild(uint16_t eid) const {
    for (const auto& child : childEndpoints) {
        if (child->getEid() == eid) {
            return child;
        }
    }
    return nullptr;
}

} // namespace iot1::endpoint
