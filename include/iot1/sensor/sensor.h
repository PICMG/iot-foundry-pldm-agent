#pragma once

#include <nlohmann/json.hpp>
#include "../pdr/pdr.h"
#include <string>
#include <memory>

using json = nlohmann::json;

namespace iot1::sensor {

/**
 * @class Sensor
 * @brief Abstract base class for all sensor types
 * 
 * Sensors read physical or logical measurements and report
 * their values through PLDM.
 */
class Sensor {
protected:
    uint16_t sensorId;
    std::string name;
    bool initialized;
    json lastValue;

    Sensor(uint16_t id, const std::string& name);

public:
    virtual ~Sensor() = default;

    // Pure virtual methods
    virtual std::string getType() const = 0;
    virtual json readValue() const = 0;
    virtual bool initialize(const json& config) = 0;
    virtual bool shutdown() = 0;
    virtual iot1::pdr::PDR getPdr() const = 0;

    // Accessors
    uint16_t getSensorId() const { return sensorId; }
    void setSensorId(uint16_t id) { sensorId = id; }

    std::string getName() const { return name; }
    void setName(const std::string& newName) { name = newName; }

    bool isInitialized() const { return initialized; }

    json getLastValue() const { return lastValue; }
};

/**
 * @class NumericSensor
 * @brief Analog/numeric measurement sensor
 */
class NumericSensor : public Sensor {
private:
    float minValue;
    float maxValue;
    float resolution;
    float tolerance;
    std::string units;

public:
    NumericSensor(uint16_t id, const std::string& name);
    ~NumericSensor() override = default;

    std::string getType() const override { return "Numeric"; }
    json readValue() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    // Numeric-specific
    void setRange(float min, float max) { minValue = min; maxValue = max; }
    void setResolution(float res) { resolution = res; }
    void setUnits(const std::string& u) { units = u; }

    float getMinValue() const { return minValue; }
    float getMaxValue() const { return maxValue; }
    float getResolution() const { return resolution; }
    std::string getUnits() const { return units; }
};

/**
 * @class StateSensor
 * @brief Discrete/state-based sensor
 */
class StateSensor : public Sensor {
private:
    std::vector<std::string> possibleStates;
    uint16_t stateSetId;

public:
    StateSensor(uint16_t id, const std::string& name);
    ~StateSensor() override = default;

    std::string getType() const override { return "State"; }
    json readValue() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    // State-specific
    void setPossibleStates(const std::vector<std::string>& states);
    const std::vector<std::string>& getPossibleStates() const { return possibleStates; }

    void setStateSetId(uint16_t id) { stateSetId = id; }
    uint16_t getStateSetId() const { return stateSetId; }
};

/**
 * @class BooleanSensor
 * @brief Binary/boolean sensor
 */
class BooleanSensor : public Sensor {
private:
    std::string trueLabel;
    std::string falseLabel;

public:
    BooleanSensor(uint16_t id, const std::string& name);
    ~BooleanSensor() override = default;

    std::string getType() const override { return "Boolean"; }
    json readValue() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    void setLabels(const std::string& trueL, const std::string& falseL) {
        trueLabel = trueL;
        falseLabel = falseL;
    }
};

/**
 * @class RateSensor
 * @brief Sensor reporting frequency/rate
 */
class RateSensor : public Sensor {
private:
    float minRate;
    float maxRate;
    std::string rateUnit;

public:
    RateSensor(uint16_t id, const std::string& name);
    ~RateSensor() override = default;

    std::string getType() const override { return "Rate"; }
    json readValue() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    void setRateRange(float min, float max) { minRate = min; maxRate = max; }
};

/**
 * @class QuadratureEncoderSensor
 * @brief Quadrature encoder for position/speed/direction
 */
class QuadratureEncoderSensor : public Sensor {
private:
    float countsPerRevolution;
    bool supportsDirection;

public:
    QuadratureEncoderSensor(uint16_t id, const std::string& name);
    ~QuadratureEncoderSensor() override = default;

    std::string getType() const override { return "QuadratureEncoder"; }
    json readValue() const override;
    bool initialize(const json& config) override;
    bool shutdown() override;
    iot1::pdr::PDR getPdr() const override;

    void setCountsPerRevolution(float cpr) { countsPerRevolution = cpr; }
    void setSupportsDirection(bool supported) { supportsDirection = supported; }
};

} // namespace iot1::sensor
