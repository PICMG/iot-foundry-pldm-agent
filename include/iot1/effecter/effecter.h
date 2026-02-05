#pragma once

#include <nlohmann/json.hpp>
#include "../pdr/pdr.h"
#include <string>
#include <memory>

using json = nlohmann::json;

namespace iot1::protocol {
class PldmTransport;
}

namespace iot1::effecter {

/**
 * @class Effecter
 * @brief Abstract base class for all effecter types
 * 
 * Effecters control physical or logical actuators through PLDM.
 */
class Effecter {
protected:
    uint16_t effecterId;
    std::string name;
    bool initialized;
    json lastCommand;

    Effecter(uint16_t id, const std::string& name);
    std::shared_ptr<::iot1::protocol::PldmTransport> transport;

public:
    virtual ~Effecter() = default;

    // Pure virtual methods
    virtual std::string getType() const = 0;
    virtual bool setCommand(const json& command) = 0;
    virtual json getStatus() const = 0;
    virtual bool initialize(const json& config) = 0;
    virtual bool shutdown() = 0;
    virtual iot1::pdr::PDR getPdr() const = 0;

    // Accessors
    uint16_t getEffecterId() const { return effecterId; }
    void setEffecterId(uint16_t id) { effecterId = id; }

    std::string getName() const { return name; }
    void setName(const std::string& newName) { name = newName; }

    bool isInitialized() const { return initialized; }

    json getLastCommand() const { return lastCommand; }
    std::shared_ptr<::iot1::protocol::PldmTransport> getTransport() const { return transport; }
    void setTransport(std::shared_ptr<::iot1::protocol::PldmTransport> xport) { transport = xport; }
};

/**
 * @class StateEffecter
 * @brief Discrete/state-based effecter (e.g., On/Off valve)
 */
class StateEffecter : public Effecter {
private:
    std::vector<std::string> possibleStates;
    uint16_t stateSetId;
    std::string currentState;

public:
    StateEffecter(uint16_t id, const std::string& name);
    ~StateEffecter() override = default;

    std::string getType() const override { return "State"; }
    bool setCommand(const json& command) override;
    json getStatus() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    // State-specific
    void setPossibleStates(const std::vector<std::string>& states);
    const std::vector<std::string>& getPossibleStates() const { return possibleStates; }

    void setStateSetId(uint16_t id) { stateSetId = id; }
    uint16_t getStateSetId() const { return stateSetId; }

    std::string getCurrentState() const { return currentState; }
};

/**
 * @class NumericEffecter
 * @brief Analog/numeric control effecter
 */
class NumericEffecter : public Effecter {
private:
    float minValue;
    float maxValue;
    float resolution;
    std::string units;
    float currentValue;

public:
    NumericEffecter(uint16_t id, const std::string& name);
    ~NumericEffecter() override = default;

    std::string getType() const override { return "Numeric"; }
    bool setCommand(const json& command) override;
    json getStatus() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    void setRange(float min, float max) { minValue = min; maxValue = max; }
    void setResolution(float res) { resolution = res; }
    void setUnits(const std::string& u) { units = u; }

    float getCurrentValue() const { return currentValue; }
};

/**
 * @class OnOffEffecter
 * @brief Binary on/off control
 */
class OnOffEffecter : public Effecter {
private:
    bool isOn;
    std::string onLabel;
    std::string offLabel;

public:
    OnOffEffecter(uint16_t id, const std::string& name);
    ~OnOffEffecter() override = default;

    std::string getType() const override { return "OnOff"; }
    bool setCommand(const json& command) override;
    json getStatus() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    bool getState() const { return isOn; }
    void setState(bool state) { isOn = state; }

    void setLabels(const std::string& onL, const std::string& offL) {
        onLabel = onL;
        offLabel = offL;
    }
};

/**
 * @class ValveEffecter
 * @brief Proportional valve control (0-100% open)
 */
class ValveEffecter : public Effecter {
private:
    float percentOpen;
    bool supportsModulation;
    float maxFlowRate;

public:
    ValveEffecter(uint16_t id, const std::string& name);
    ~ValveEffecter() override = default;

    std::string getType() const override { return "Valve"; }
    bool setCommand(const json& command) override;
    json getStatus() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    float getPercentOpen() const { return percentOpen; }
    void setPercentOpen(float percent) { 
        percentOpen = (percent < 0.0f) ? 0.0f : (percent > 100.0f) ? 100.0f : percent;
    }
};

/**
 * @class RelativeEffecter
 * @brief Relative/incremental control (increase/decrease)
 */
class RelativeEffecter : public Effecter {
private:
    float stepSize;
    float minValue;
    float maxValue;
    float currentValue;

public:
    RelativeEffecter(uint16_t id, const std::string& name);
    ~RelativeEffecter() override = default;

    std::string getType() const override { return "Relative"; }
    bool setCommand(const json& command) override;
    json getStatus() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    float getCurrentValue() const { return currentValue; }
    float getStepSize() const { return stepSize; }
};

} // namespace iot1::effecter
