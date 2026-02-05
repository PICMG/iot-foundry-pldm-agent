#pragma once

#include <nlohmann/json.hpp>
#include "../sensor/sensor.h"
#include "../effecter/effecter.h"
#include <string>
#include <memory>
#include <vector>

using json = nlohmann::json;

namespace iot1::protocol {
class PldmTransport;
}

namespace iot1::controller {

/**
 * @class Controller
 * @brief Abstract base class for control algorithms
 * 
 * Controllers read sensor inputs and drive effecter outputs
 * to achieve desired setpoints or system behavior.
 */
class Controller {
protected:
    uint16_t controllerId;
    std::string name;
    bool initialized;
    bool enabled;
    json lastOutput;

    Controller(uint16_t id, const std::string& name);
    std::shared_ptr<::iot1::protocol::PldmTransport> transport;

public:
    virtual ~Controller() = default;

    // Pure virtual methods
    virtual std::string getType() const = 0;
    virtual bool initialize(const json& config) = 0;
    virtual bool shutdown() = 0;
    virtual json update(const json& sensorData) = 0;
    virtual json getStatus() const = 0;

    // Control methods
    virtual bool enable() { enabled = true; return true; }
    virtual bool disable() { enabled = false; return true; }

    // Accessors
    uint16_t getControllerId() const { return controllerId; }
    void setControllerId(uint16_t id) { controllerId = id; }

    std::string getName() const { return name; }
    void setName(const std::string& newName) { name = newName; }

    bool isInitialized() const { return initialized; }
    bool isEnabled() const { return enabled; }
    std::shared_ptr<::iot1::protocol::PldmTransport> getTransport() const { return transport; }
    void setTransport(std::shared_ptr<::iot1::protocol::PldmTransport> xport) { transport = xport; }
};

/**
 * @class PidController
 * @brief Proportional-Integral-Derivative controller
 * 
 * Standard PID control loop: output = Kp*error + Ki*integral + Kd*derivative
 */
class PidController : public Controller {
private:
    float setpoint;
    float kp;  // Proportional gain
    float ki;  // Integral gain
    float kd;  // Derivative gain
    float integral;
    float lastError;
    float minOutput;
    float maxOutput;
    float integralLimit;

public:
    PidController(uint16_t id, const std::string& name);
    ~PidController() override = default;

    std::string getType() const override { return "PID"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json update(const json& sensorData) override;
    json getStatus() const override;

    // PID-specific setters
    void setGains(float p, float i, float d) { kp = p; ki = i; kd = d; }
    void setSetpoint(float sp) { setpoint = sp; }
    void setOutputLimits(float min, float max) { minOutput = min; maxOutput = max; }
    void setIntegralLimit(float limit) { integralLimit = limit; }

    // Getters
    float getSetpoint() const { return setpoint; }
    float getKp() const { return kp; }
    float getKi() const { return ki; }
    float getKd() const { return kd; }
};

/**
 * @class ProfiledMotionController
 * @brief Trapezoidal motion profile controller
 * 
 * Generates smooth motion with constant acceleration/deceleration phases
 * and constant velocity phase.
 */
class ProfiledMotionController : public Controller {
private:
    float targetPosition;
    float currentPosition;
    float currentVelocity;
    float maxVelocity;
    float maxAcceleration;
    float maxDeceleration;
    float profileTime;
    float profileElapsed;

    enum class Phase {
        Accelerating,
        Constant,
        Decelerating,
        Idle
    };
    Phase currentPhase;

public:
    ProfiledMotionController(uint16_t id, const std::string& name);
    ~ProfiledMotionController() override = default;

    std::string getType() const override { return "ProfiledMotion"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json update(const json& sensorData) override;
    json getStatus() const override;

    // Motion-specific setters
    void setProfile(float maxVel, float maxAccel, float maxDecel) {
        maxVelocity = maxVel;
        maxAcceleration = maxAccel;
        maxDeceleration = maxDecel;
    }

    void setTargetPosition(float pos) { targetPosition = pos; }
    float getTargetPosition() const { return targetPosition; }
    float getCurrentPosition() const { return currentPosition; }
    float getCurrentVelocity() const { return currentVelocity; }

private:
    void updateProfilePhase(float dt);
    void calculateProfile();
};

/**
 * @class OnOffController
 * @brief Binary on/off control with hysteresis
 * 
 * Useful for temperature, pressure, or level control with
 * hysteresis band to prevent oscillation.
 */
class OnOffController : public Controller {
private:
    float setpoint;
    float hysteresis;
    bool currentState;

public:
    OnOffController(uint16_t id, const std::string& name);
    ~OnOffController() override = default;

    std::string getType() const override { return "OnOff"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json update(const json& sensorData) override;
    json getStatus() const override;

    void setSetpoint(float sp) { setpoint = sp; }
    void setHysteresis(float h) { hysteresis = h; }

    float getSetpoint() const { return setpoint; }
    float getHysteresis() const { return hysteresis; }
    bool getState() const { return currentState; }
};

/**
 * @class AdaptiveController
 * @brief Adaptive control that adjusts gains based on system behavior
 * 
 * Monitors system response and adjusts PID gains to maintain
 * stable, responsive control.
 */
class AdaptiveController : public Controller {
private:
    float setpoint;
    float kp, ki, kd;
    float integral;
    float lastError;
    float minOutput, maxOutput;
    float responseTime;
    float overshoot;
    int updateCount;

public:
    AdaptiveController(uint16_t id, const std::string& name);
    ~AdaptiveController() override = default;

    std::string getType() const override { return "Adaptive"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json update(const json& sensorData) override;
    json getStatus() const override;

    void setSetpoint(float sp) { setpoint = sp; }
    void setInitialGains(float p, float i, float d) { kp = p; ki = i; kd = d; }
    void setOutputLimits(float min, float max) { minOutput = min; maxOutput = max; }

private:
    void adaptGains(float error);
};

} // namespace iot1::controller
