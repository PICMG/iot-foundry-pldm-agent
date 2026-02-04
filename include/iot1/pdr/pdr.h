#pragma once

#include <nlohmann/json.hpp>
#include <cstdint>
#include <vector>
#include <string>
#include <stdexcept>

using json = nlohmann::json;

namespace iot1::pdr {

/**
 * @class PDR
 * @brief Generic Platform Data Record wrapper
 * 
 * Provides dictionary-like access to PDR fields while maintaining
 * PLDM compliance and validation. Internal representation is JSON
 * for flexibility and ease of extension.
 */
class PDR {
private:
    json pdrData;

public:
    // Constructors
    PDR() = default;
    explicit PDR(const json& data);
    PDR(const PDR&) = default;
    PDR(PDR&&) = default;
    PDR& operator=(const PDR&) = default;
    PDR& operator=(PDR&&) = default;
    ~PDR() = default;

    // Dictionary-like access
    json& operator[](const std::string& key);
    const json& operator[](const std::string& key) const;

    // Type-safe accessors with default values
    template<typename T>
    T get(const std::string& key, const T& defaultValue = T()) const {
        try {
            if (pdrData.contains(key)) {
                return pdrData[key].get<T>();
            }
        } catch (const json::exception& e) {
            // Type mismatch or invalid access
            throw std::runtime_error(std::string("PDR field access error: ") + e.what());
        }
        return defaultValue;
    }

    // Type-safe setters
    template<typename T>
    void set(const std::string& key, const T& value) {
        pdrData[key] = value;
    }

    // Common PDR fields (PLDM standard)
    uint32_t getRecordHandle() const { return get<uint32_t>("recordHandle", 0); }
    void setRecordHandle(uint32_t handle) { set("recordHandle", handle); }

    uint8_t getPdrHeaderVersion() const { return get<uint8_t>("pdrHeaderVersion", 1); }
    void setPdrHeaderVersion(uint8_t version) { set("pdrHeaderVersion", version); }

    uint8_t getPdrType() const { return get<uint8_t>("pdrType", 0); }
    void setPdrType(uint8_t type) { set("pdrType", type); }

    uint16_t getRecordChangeNumber() const { return get<uint16_t>("recordChangeNumber", 0); }
    void setRecordChangeNumber(uint16_t number) { set("recordChangeNumber", number); }

    uint16_t getDataLength() const { return get<uint16_t>("dataLength", 0); }
    void setDataLength(uint16_t length) { set("dataLength", length); }

    uint16_t getPldmTerminusHandle() const { return get<uint16_t>("pldmTerminusHandle", 1); }
    void setPldmTerminusHandle(uint16_t handle) { set("pldmTerminusHandle", handle); }

    // Entity-related fields
    uint16_t getEntityType() const { return get<uint16_t>("entityType", 0); }
    void setEntityType(uint16_t type) { set("entityType", type); }

    uint16_t getEntityInstanceNumber() const { return get<uint16_t>("entityInstanceNumber", 0); }
    void setEntityInstanceNumber(uint16_t number) { set("entityInstanceNumber", number); }

    uint16_t getContainerId() const { return get<uint16_t>("containerId", 0); }
    void setContainerId(uint16_t id) { set("containerId", id); }

    // Sensor-specific fields
    uint16_t getSensorId() const { return get<uint16_t>("sensorId", 0); }
    void setSensorId(uint16_t id) { set("sensorId", id); }

    // Effecter-specific fields
    uint16_t getEffecterId() const { return get<uint16_t>("effecterId", 0); }
    void setEffecterId(uint16_t id) { set("effecterId", id); }

    // Check if field exists
    bool hasField(const std::string& key) const { return pdrData.contains(key); }

    // Get all fields
    const json& getData() const { return pdrData; }
    json& getData() { return pdrData; }

    // Validate PDR structure
    bool validate() const;

    // JSON conversion
    json toJson() const { return pdrData; }
    static PDR fromJson(const json& data);

    // String representation
    std::string toString() const { return pdrData.dump(2); }

    // Comparison
    bool operator==(const PDR& other) const { return pdrData == other.pdrData; }
    bool operator!=(const PDR& other) const { return pdrData != other.pdrData; }

    // Serialization to/from binary PLDM format
    std::vector<uint8_t> toBinary() const;
    static PDR fromBinary(const std::vector<uint8_t>& data);

    // Clear all fields
    void clear() { pdrData.clear(); }

    // Number of fields
    size_t size() const { return pdrData.size(); }
};

} // namespace iot1::pdr
