#pragma once

#include <nlohmann/json.hpp>
#include <string>
#include <memory>

using json = nlohmann::json;

namespace iot1::protocol {
class PldmTransport;  // Forward declaration
}

namespace iot1::endpoint {

class PDRRepository;  // Forward declaration

/**
 * @class Endpoint
 * @brief Abstract base class for all PICMG IoT.1 endpoints
 * 
 * All endpoint types (Simple, PID Control, Profiled Motion, etc.)
 * inherit from this class and implement the virtual methods.
 */
class Endpoint {
protected:
    uint16_t eid;                          // MCTP Endpoint ID
    std::string name;                      // Friendly name
    std::shared_ptr<PDRRepository> pdrRepo; // PDR repository
    bool initialized;

    Endpoint(uint16_t eid, const std::string& name);
    std::shared_ptr<::iot1::protocol::PldmTransport> transport;

public:
    virtual ~Endpoint() = default;

    // Pure virtual methods - must be implemented by derived classes
    virtual std::string getType() const = 0;
    virtual bool initialize(const json& config) = 0;
    virtual bool shutdown() = 0;
    virtual json getCapabilities() const = 0;
    virtual json getStatus() const = 0;

    // Accessors
    uint16_t getEid() const { return eid; }
    void setEid(uint16_t newEid) { eid = newEid; }

    std::string getName() const { return name; }
    void setName(const std::string& newName) { name = newName; }

    bool isInitialized() const { return initialized; }

    std::shared_ptr<PDRRepository> getPdrRepository() const { return pdrRepo; }
    void setPdrRepository(std::shared_ptr<PDRRepository> repo) { pdrRepo = repo; }
    std::shared_ptr<::iot1::protocol::PldmTransport> getTransport() const { return transport; }
    void setTransport(std::shared_ptr<::iot1::protocol::PldmTransport> xport) { transport = xport; }
};

/**
 * @class SimpleEndpoint
 * @brief Simple sensor/effecter endpoint
 */
class SimpleEndpoint : public Endpoint {
public:
    SimpleEndpoint(uint16_t eid, const std::string& name);
    ~SimpleEndpoint() override = default;

    std::string getType() const override { return "Simple"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json getCapabilities() const override;
    json getStatus() const override;
};

/**
 * @class PidControlEndpoint
 * @brief PID Controller endpoint
 */
class PidControlEndpoint : public Endpoint {
private:
    float proportionalGain;
    float integralGain;
    float derivativeGain;
    float setpoint;
    float outputLimit;

public:
    PidControlEndpoint(uint16_t eid, const std::string& name);
    ~PidControlEndpoint() override = default;

    std::string getType() const override { return "PID"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json getCapabilities() const override;
    json getStatus() const override;

    // PID-specific methods
    void setGains(float kp, float ki, float kd);
    void setSetpoint(float sp);
    float getSetpoint() const { return setpoint; }
};

/**
 * @class ProfiledMotionControlEndpoint
 * @brief Profiled Motion Controller endpoint
 */
class ProfiledMotionControlEndpoint : public Endpoint {
private:
    float acceleration;
    float velocity;
    float deceleration;
    float positionSetpoint;

public:
    ProfiledMotionControlEndpoint(uint16_t eid, const std::string& name);
    ~ProfiledMotionControlEndpoint() override = default;

    std::string getType() const override { return "ProfiledMotion"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json getCapabilities() const override;
    json getStatus() const override;

    // Motion-specific methods
    void setProfile(float accel, float vel, float decel);
    void setPosition(float pos);
};

/**
 * @class CompositeEndpoint
 * @brief Composite endpoint managing multiple devices
 */
class CompositeEndpoint : public Endpoint {
private:
    std::vector<std::shared_ptr<Endpoint>> childEndpoints;

public:
    CompositeEndpoint(uint16_t eid, const std::string& name);
    ~CompositeEndpoint() override = default;

    std::string getType() const override { return "Composite"; }
    bool initialize(const json& config) override;
    bool shutdown() override;
    json getCapabilities() const override;
    json getStatus() const override;

    // Composite-specific methods
    void addChild(std::shared_ptr<Endpoint> endpoint);
    void removeChild(uint16_t eid);
    std::shared_ptr<Endpoint> getChild(uint16_t eid) const;
    const std::vector<std::shared_ptr<Endpoint>>& getChildren() const { return childEndpoints; }
};

} // namespace iot1::endpoint
