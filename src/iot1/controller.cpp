#include "controller.h"
#include <cmath>
#include <iostream>
#include <chrono>

namespace iot1::controller {

// Base Controller
Controller::Controller(uint16_t id, const std::string& name)
    : controllerId(id), name(name), initialized(false), enabled(false) {}

// PidController
PidController::PidController(uint16_t id, const std::string& name)
    : Controller(id, name), setpoint(0.0f), kp(1.0f), ki(0.0f), kd(0.0f),
      integral(0.0f), lastError(0.0f), minOutput(-100.0f), maxOutput(100.0f),
      integralLimit(10.0f) {}

bool PidController::initialize(const json& config) {
    try {
        if (config.contains("setpoint")) setpoint = config["setpoint"];
        if (config.contains("kp")) kp = config["kp"];
        if (config.contains("ki")) ki = config["ki"];
        if (config.contains("kd")) kd = config["kd"];
        if (config.contains("minOutput")) minOutput = config["minOutput"];
        if (config.contains("maxOutput")) maxOutput = config["maxOutput"];
        if (config.contains("integralLimit")) integralLimit = config["integralLimit"];

        integral = 0.0f;
        lastError = 0.0f;
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize PidController: " << e.what() << std::endl;
        return false;
    }
}

bool PidController::shutdown() {
    initialized = false;
    enabled = false;
    integral = 0.0f;
    return true;
}

json PidController::update(const json& sensorData) {
    if (!enabled || !initialized) {
        return json{{"error", "Controller not enabled or initialized"}};
    }

    try {
        float feedback = sensorData.value("value", 0.0f);
        float error = setpoint - feedback;

        // Proportional term
        float p = kp * error;

        // Integral term with anti-windup
        integral += error;
        if (std::abs(integral) > integralLimit) {
            integral = (integral > 0) ? integralLimit : -integralLimit;
        }
        float i = ki * integral;

        // Derivative term
        float d = kd * (error - lastError);
        lastError = error;

        // Sum and clamp output
        float output = p + i + d;
        if (output > maxOutput) output = maxOutput;
        if (output < minOutput) output = minOutput;

        lastOutput = json{
            {"controllerId", controllerId},
            {"type", "PID"},
            {"output", output},
            {"error", error},
            {"setpoint", setpoint},
            {"feedback", feedback},
            {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
        };

        return lastOutput;
    } catch (const std::exception& e) {
        std::cerr << "PID update failed: " << e.what() << std::endl;
        return json{{"error", e.what()}};
    }
}

json PidController::getStatus() const {
    return json{
        {"controllerId", controllerId},
        {"type", "PID"},
        {"name", name},
        {"enabled", enabled},
        {"setpoint", setpoint},
        {"gains", {{"kp", kp}, {"ki", ki}, {"kd", kd}}},
        {"limits", {{"min", minOutput}, {"max", maxOutput}}},
        {"integral", integral}
    };
}

// ProfiledMotionController
ProfiledMotionController::ProfiledMotionController(uint16_t id, const std::string& name)
    : Controller(id, name), targetPosition(0.0f), currentPosition(0.0f),
      currentVelocity(0.0f), maxVelocity(1.0f), maxAcceleration(0.1f),
      maxDeceleration(0.1f), profileTime(0.0f), profileElapsed(0.0f),
      currentPhase(Phase::Idle) {}

bool ProfiledMotionController::initialize(const json& config) {
    try {
        if (config.contains("targetPosition")) targetPosition = config["targetPosition"];
        if (config.contains("currentPosition")) currentPosition = config["currentPosition"];
        if (config.contains("maxVelocity")) maxVelocity = config["maxVelocity"];
        if (config.contains("maxAcceleration")) maxAcceleration = config["maxAcceleration"];
        if (config.contains("maxDeceleration")) maxDeceleration = config["maxDeceleration"];

        currentPhase = Phase::Idle;
        profileElapsed = 0.0f;
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize ProfiledMotionController: " << e.what() << std::endl;
        return false;
    }
}

bool ProfiledMotionController::shutdown() {
    initialized = false;
    enabled = false;
    currentVelocity = 0.0f;
    currentPhase = Phase::Idle;
    return true;
}

json ProfiledMotionController::update(const json& sensorData) {
    if (!enabled || !initialized) {
        return json{{"error", "Controller not enabled or initialized"}};
    }

    try {
        // Get current position from sensor
        float feedback = sensorData.value("position", currentPosition);
        currentPosition = feedback;

        // Check if we've reached target
        float positionError = targetPosition - currentPosition;
        if (std::abs(positionError) < 0.01f) {
            currentVelocity = 0.0f;
            currentPhase = Phase::Idle;
        } else {
            calculateProfile();
            updateProfilePhase(0.01f);  // Assume 10ms update rate
        }

        lastOutput = json{
            {"controllerId", controllerId},
            {"type", "ProfiledMotion"},
            {"position", currentPosition},
            {"targetPosition", targetPosition},
            {"velocity", currentVelocity},
            {"phase", static_cast<int>(currentPhase)},
            {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
        };

        return lastOutput;
    } catch (const std::exception& e) {
        std::cerr << "Motion update failed: " << e.what() << std::endl;
        return json{{"error", e.what()}};
    }
}

json ProfiledMotionController::getStatus() const {
    return json{
        {"controllerId", controllerId},
        {"type", "ProfiledMotion"},
        {"name", name},
        {"enabled", enabled},
        {"currentPosition", currentPosition},
        {"targetPosition", targetPosition},
        {"currentVelocity", currentVelocity},
        {"maxVelocity", maxVelocity},
        {"profile", {
            {"maxAcceleration", maxAcceleration},
            {"maxDeceleration", maxDeceleration}
        }}
    };
}

void ProfiledMotionController::calculateProfile() {
    // Simple trapezoidal profile calculation
    float distance = targetPosition - currentPosition;
    if (std::abs(distance) < 0.001f) return;

    // Time to reach max velocity
    float tAccel = maxVelocity / maxAcceleration;
    float tDecel = maxVelocity / maxDeceleration;

    // Distance during accel/decel
    float dAccel = 0.5f * maxAcceleration * tAccel * tAccel;
    float dDecel = 0.5f * maxDeceleration * tDecel * tDecel;

    if (2.0f * dAccel >= std::abs(distance)) {
        // Triangle profile - limit max velocity
        maxVelocity = std::sqrt(std::abs(distance) * maxAcceleration / 2.0f);
    }
}

void ProfiledMotionController::updateProfilePhase(float dt) {
    float positionError = targetPosition - currentPosition;
    int direction = (positionError > 0) ? 1 : -1;

    if (std::abs(positionError) < 0.01f) {
        currentPhase = Phase::Idle;
        currentVelocity = 0.0f;
    } else if (std::abs(currentVelocity) < maxVelocity) {
        currentPhase = Phase::Accelerating;
        currentVelocity += direction * maxAcceleration * dt;
    } else if (std::abs(currentVelocity) >= maxVelocity) {
        currentPhase = Phase::Constant;
        currentVelocity = direction * maxVelocity;
    }

    // Check if we should start decelerating
    float stoppingDistance = (currentVelocity * currentVelocity) / (2.0f * maxDeceleration);
    if (std::abs(stoppingDistance) >= std::abs(positionError)) {
        currentPhase = Phase::Decelerating;
        currentVelocity -= direction * maxDeceleration * dt;
    }
}

// OnOffController
OnOffController::OnOffController(uint16_t id, const std::string& name)
    : Controller(id, name), setpoint(0.0f), hysteresis(1.0f), currentState(false) {}

bool OnOffController::initialize(const json& config) {
    try {
        if (config.contains("setpoint")) setpoint = config["setpoint"];
        if (config.contains("hysteresis")) hysteresis = config["hysteresis"];
        if (config.contains("initialState")) currentState = config["initialState"];

        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize OnOffController: " << e.what() << std::endl;
        return false;
    }
}

bool OnOffController::shutdown() {
    initialized = false;
    enabled = false;
    currentState = false;
    return true;
}

json OnOffController::update(const json& sensorData) {
    if (!enabled || !initialized) {
        return json{{"error", "Controller not enabled or initialized"}};
    }

    try {
        float feedback = sensorData.value("value", 0.0f);

        // Hysteresis logic
        if (currentState) {
            if (feedback < (setpoint - hysteresis / 2.0f)) {
                currentState = false;
            }
        } else {
            if (feedback > (setpoint + hysteresis / 2.0f)) {
                currentState = true;
            }
        }

        lastOutput = json{
            {"controllerId", controllerId},
            {"type", "OnOff"},
            {"state", currentState},
            {"feedback", feedback},
            {"setpoint", setpoint},
            {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
        };

        return lastOutput;
    } catch (const std::exception& e) {
        std::cerr << "OnOff update failed: " << e.what() << std::endl;
        return json{{"error", e.what()}};
    }
}

json OnOffController::getStatus() const {
    return json{
        {"controllerId", controllerId},
        {"type", "OnOff"},
        {"name", name},
        {"enabled", enabled},
        {"currentState", currentState},
        {"setpoint", setpoint},
        {"hysteresis", hysteresis}
    };
}

// AdaptiveController
AdaptiveController::AdaptiveController(uint16_t id, const std::string& name)
    : Controller(id, name), setpoint(0.0f), kp(1.0f), ki(0.0f), kd(0.0f),
      integral(0.0f), lastError(0.0f), minOutput(-100.0f), maxOutput(100.0f),
      responseTime(0.0f), overshoot(0.0f), updateCount(0) {}

bool AdaptiveController::initialize(const json& config) {
    try {
        if (config.contains("setpoint")) setpoint = config["setpoint"];
        if (config.contains("kp")) kp = config["kp"];
        if (config.contains("ki")) ki = config["ki"];
        if (config.contains("kd")) kd = config["kd"];
        if (config.contains("minOutput")) minOutput = config["minOutput"];
        if (config.contains("maxOutput")) maxOutput = config["maxOutput"];

        integral = 0.0f;
        lastError = 0.0f;
        updateCount = 0;
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize AdaptiveController: " << e.what() << std::endl;
        return false;
    }
}

bool AdaptiveController::shutdown() {
    initialized = false;
    enabled = false;
    integral = 0.0f;
    return true;
}

json AdaptiveController::update(const json& sensorData) {
    if (!enabled || !initialized) {
        return json{{"error", "Controller not enabled or initialized"}};
    }

    try {
        float feedback = sensorData.value("value", 0.0f);
        float error = setpoint - feedback;

        // Standard PID calculation
        float p = kp * error;

        integral += error;
        integral = (integral > 10.0f) ? 10.0f : (integral < -10.0f) ? -10.0f : integral;
        float i = ki * integral;

        float d = kd * (error - lastError);
        lastError = error;

        // Adapt gains based on system behavior
        adaptGains(error);

        float output = p + i + d;
        if (output > maxOutput) output = maxOutput;
        if (output < minOutput) output = minOutput;

        lastOutput = json{
            {"controllerId", controllerId},
            {"type", "Adaptive"},
            {"output", output},
            {"error", error},
            {"setpoint", setpoint},
            {"feedback", feedback},
            {"adaptiveGains", {{"kp", kp}, {"ki", ki}, {"kd", kd}}},
            {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
        };

        return lastOutput;
    } catch (const std::exception& e) {
        std::cerr << "Adaptive update failed: " << e.what() << std::endl;
        return json{{"error", e.what()}};
    }
}

json AdaptiveController::getStatus() const {
    return json{
        {"controllerId", controllerId},
        {"type", "Adaptive"},
        {"name", name},
        {"enabled", enabled},
        {"setpoint", setpoint},
        {"adaptiveGains", {{"kp", kp}, {"ki", ki}, {"kd", kd}}},
        {"limits", {{"min", minOutput}, {"max", maxOutput}}},
        {"responseMetrics", {{"responseTime", responseTime}, {"overshoot", overshoot}}}
    };
}

void AdaptiveController::adaptGains(float error) {
    updateCount++;

    // Simple adaptation: reduce overshoot if we're oscillating
    if (updateCount % 10 == 0) {
        if (error * lastError < 0) {  // Sign change indicates oscillation
            kd *= 1.05f;  // Increase damping
        } else if (std::abs(error) > 0.1f) {
            kp *= 1.01f;  // Increase responsiveness
        }
    }

    // Keep gains in reasonable bounds
    if (kp > 10.0f) kp = 10.0f;
    if (kd > 5.0f) kd = 5.0f;
}

} // namespace iot1::controller
