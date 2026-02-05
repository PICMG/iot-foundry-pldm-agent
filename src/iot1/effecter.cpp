#include "iot1/effecter/effecter.h"
#include <iostream>
#include <chrono>
#include <algorithm>

namespace iot1::effecter {

// Base Effecter
Effecter::Effecter(uint16_t id, const std::string& name)
    : effecterId(id), name(name), initialized(false) {}

// StateEffecter
StateEffecter::StateEffecter(uint16_t id, const std::string& name)
    : Effecter(id, name), stateSetId(0) {}

bool StateEffecter::setCommand(const json& command) {
    try {
        if (command.contains("state")) {
            std::string newState = command["state"];
            // Validate state
            auto it = std::find(possibleStates.begin(), possibleStates.end(), newState);
            if (it != possibleStates.end()) {
                currentState = newState;
                lastCommand = command;
                return true;
            } else {
                std::cerr << "Invalid state: " << newState << std::endl;
                return false;
            }
        }
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Failed to set state: " << e.what() << std::endl;
        return false;
    }
}

json StateEffecter::getStatus() const {
    return json{
        {"effecterId", effecterId},
        {"type", "State"},
        {"state", currentState},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
}

bool StateEffecter::initialize(const json& config) {
    try {
        if (config.contains("possibleStates")) {
            possibleStates = config["possibleStates"].get<std::vector<std::string>>();
        }
        if (config.contains("stateSetId")) stateSetId = config["stateSetId"];
        if (config.contains("initialState")) currentState = config["initialState"];
        if (possibleStates.empty() && !currentState.empty()) {
            possibleStates.push_back(currentState);
        }
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize StateEffecter: " << e.what() << std::endl;
        return false;
    }
}

bool StateEffecter::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR StateEffecter::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x0C);  // State Effecter PDR type
    pdr.setEffecterId(effecterId);
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

void StateEffecter::setPossibleStates(const std::vector<std::string>& states) {
    possibleStates = states;
}

// NumericEffecter
NumericEffecter::NumericEffecter(uint16_t id, const std::string& name)
    : Effecter(id, name), minValue(0.0f), maxValue(100.0f), 
      resolution(0.1f), units(""), currentValue(0.0f) {}

bool NumericEffecter::setCommand(const json& command) {
    try {
        if (command.contains("value")) {
            float newValue = command["value"];
            if (newValue >= minValue && newValue <= maxValue) {
                currentValue = newValue;
                lastCommand = command;
                return true;
            } else {
                std::cerr << "Value out of range: " << newValue << std::endl;
                return false;
            }
        }
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Failed to set numeric value: " << e.what() << std::endl;
        return false;
    }
}

json NumericEffecter::getStatus() const {
    return json{
        {"effecterId", effecterId},
        {"type", "Numeric"},
        {"value", currentValue},
        {"units", units},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
}

bool NumericEffecter::initialize(const json& config) {
    try {
        if (config.contains("minValue")) minValue = config["minValue"];
        if (config.contains("maxValue")) maxValue = config["maxValue"];
        if (config.contains("resolution")) resolution = config["resolution"];
        if (config.contains("units")) units = config["units"];
        if (config.contains("initialValue")) currentValue = config["initialValue"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize NumericEffecter: " << e.what() << std::endl;
        return false;
    }
}

bool NumericEffecter::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR NumericEffecter::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x10);  // Numeric Effecter PDR type
    pdr.setEffecterId(effecterId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["minValue"] = minValue;
    pdr["maxValue"] = maxValue;
    pdr["resolution"] = resolution;
    pdr["units"] = units;
    
    return pdr;
}

// OnOffEffecter
OnOffEffecter::OnOffEffecter(uint16_t id, const std::string& name)
    : Effecter(id, name), isOn(false), onLabel("On"), offLabel("Off") {}

bool OnOffEffecter::setCommand(const json& command) {
    try {
        if (command.contains("value")) {
            isOn = command["value"];
            lastCommand = command;
            return true;
        }
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Failed to set on/off: " << e.what() << std::endl;
        return false;
    }
}

json OnOffEffecter::getStatus() const {
    return json{
        {"effecterId", effecterId},
        {"type", "OnOff"},
        {"value", isOn},
        {"label", isOn ? onLabel : offLabel},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
}

bool OnOffEffecter::initialize(const json& config) {
    try {
        if (config.contains("onLabel")) onLabel = config["onLabel"];
        if (config.contains("offLabel")) offLabel = config["offLabel"];
        if (config.contains("initialValue")) isOn = config["initialValue"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize OnOffEffecter: " << e.what() << std::endl;
        return false;
    }
}

bool OnOffEffecter::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR OnOffEffecter::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x0C);  // State Effecter PDR type
    pdr.setEffecterId(effecterId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["stateSetId"] = 0;  // Boolean state set
    pdr["possibleStates"] = json::array({offLabel, onLabel});
    
    return pdr;
}

// ValveEffecter
ValveEffecter::ValveEffecter(uint16_t id, const std::string& name)
    : Effecter(id, name), percentOpen(0.0f), supportsModulation(true), maxFlowRate(100.0f) {}

bool ValveEffecter::setCommand(const json& command) {
    try {
        if (command.contains("percentOpen")) {
            setPercentOpen(command["percentOpen"]);
            lastCommand = command;
            return true;
        }
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Failed to set valve position: " << e.what() << std::endl;
        return false;
    }
}

json ValveEffecter::getStatus() const {
    return json{
        {"effecterId", effecterId},
        {"type", "Valve"},
        {"percentOpen", percentOpen},
        {"currentFlow", (percentOpen / 100.0f) * maxFlowRate},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
}

bool ValveEffecter::initialize(const json& config) {
    try {
        if (config.contains("supportsModulation")) supportsModulation = config["supportsModulation"];
        if (config.contains("maxFlowRate")) maxFlowRate = config["maxFlowRate"];
        if (config.contains("initialPercentOpen")) setPercentOpen(config["initialPercentOpen"]);
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize ValveEffecter: " << e.what() << std::endl;
        return false;
    }
}

bool ValveEffecter::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR ValveEffecter::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x10);  // Numeric Effecter PDR type
    pdr.setEffecterId(effecterId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["minValue"] = 0.0f;
    pdr["maxValue"] = 100.0f;
    pdr["units"] = "%";
    pdr["supportsModulation"] = supportsModulation;
    pdr["maxFlowRate"] = maxFlowRate;
    
    return pdr;
}

// RelativeEffecter
RelativeEffecter::RelativeEffecter(uint16_t id, const std::string& name)
    : Effecter(id, name), stepSize(1.0f), minValue(0.0f), maxValue(100.0f), currentValue(0.0f) {}

bool RelativeEffecter::setCommand(const json& command) {
    try {
        if (command.contains("steps")) {
            float steps = command["steps"];
            float newValue = currentValue + (steps * stepSize);
            if (newValue >= minValue && newValue <= maxValue) {
                currentValue = newValue;
                lastCommand = command;
                return true;
            } else {
                std::cerr << "Would exceed bounds" << std::endl;
                return false;
            }
        }
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Failed to set relative value: " << e.what() << std::endl;
        return false;
    }
}

json RelativeEffecter::getStatus() const {
    return json{
        {"effecterId", effecterId},
        {"type", "Relative"},
        {"value", currentValue},
        {"stepSize", stepSize},
        {"timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
    };
}

bool RelativeEffecter::initialize(const json& config) {
    try {
        if (config.contains("stepSize")) stepSize = config["stepSize"];
        if (config.contains("minValue")) minValue = config["minValue"];
        if (config.contains("maxValue")) maxValue = config["maxValue"];
        if (config.contains("initialValue")) currentValue = config["initialValue"];
        initialized = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize RelativeEffecter: " << e.what() << std::endl;
        return false;
    }
}

bool RelativeEffecter::shutdown() {
    initialized = false;
    return true;
}

iot1::pdr::PDR RelativeEffecter::getPdr() const {
    iot1::pdr::PDR pdr;
    pdr.setPdrType(0x10);  // Numeric Effecter PDR type
    pdr.setEffecterId(effecterId);
    pdr.setEntityType(0x6000);
    pdr.setEntityInstanceNumber(1);
    pdr.setContainerId(1);
    
    pdr["minValue"] = minValue;
    pdr["maxValue"] = maxValue;
    pdr["stepSize"] = stepSize;
    pdr["type"] = "Relative";
    
    return pdr;
}

} // namespace iot1::effecter
