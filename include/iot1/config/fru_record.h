#pragma once

#include <nlohmann/json.hpp>
#include <string>
#include <stdexcept>

using json = nlohmann::json;

namespace iot1::config {

/**
 * @class FruRecord
 * @brief Generic FRU (Field Replaceable Unit) Record wrapper
 * 
 * Provides dictionary-like access to FRU fields while maintaining
 * compliance with PLDM FRU specification. Uses JSON for flexibility.
 */
class FruRecord {
private:
    json fruData;

public:
    // Constructors
    FruRecord() = default;
    explicit FruRecord(const json& data);
    FruRecord(const FruRecord&) = default;
    FruRecord(FruRecord&&) = default;
    FruRecord& operator=(const FruRecord&) = default;
    FruRecord& operator=(FruRecord&&) = default;
    ~FruRecord() = default;

    // Dictionary-like access
    json& operator[](const std::string& key);
    const json& operator[](const std::string& key) const;

    // Type-safe accessors with default values
    template<typename T>
    T get(const std::string& key, const T& defaultValue = T()) const {
        try {
            if (fruData.contains(key)) {
                return fruData[key].get<T>();
            }
        } catch (const json::exception& e) {
            throw std::runtime_error(std::string("FRU field access error: ") + e.what());
        }
        return defaultValue;
    }

    // Type-safe setters
    template<typename T>
    void set(const std::string& key, const T& value) {
        fruData[key] = value;
    }

    // Common FRU fields
    std::string getManufacturer() const { return get<std::string>("manufacturer", ""); }
    void setManufacturer(const std::string& mfg) { set("manufacturer", mfg); }

    std::string getProductName() const { return get<std::string>("productName", ""); }
    void setProductName(const std::string& name) { set("productName", name); }

    std::string getProductVersion() const { return get<std::string>("productVersion", ""); }
    void setProductVersion(const std::string& version) { set("productVersion", version); }

    std::string getSerialNumber() const { return get<std::string>("serialNumber", ""); }
    void setSerialNumber(const std::string& serial) { set("serialNumber", serial); }

    std::string getAssetTag() const { return get<std::string>("assetTag", ""); }
    void setAssetTag(const std::string& tag) { set("assetTag", tag); }

    // FRU chassis type
    uint8_t getChassisType() const { return get<uint8_t>("chassisType", 0); }
    void setChassisType(uint8_t type) { set("chassisType", type); }

    // Board/Module specific
    std::string getBoardType() const { return get<std::string>("boardType", ""); }
    void setBoardType(const std::string& type) { set("boardType", type); }

    // Check if field exists
    bool hasField(const std::string& key) const { return fruData.contains(key); }

    // Get all fields
    const json& getData() const { return fruData; }
    json& getData() { return fruData; }

    // Validate FRU structure
    bool validate() const;

    // JSON conversion
    json toJson() const { return fruData; }
    static FruRecord fromJson(const json& data);

    // String representation
    std::string toString() const { return fruData.dump(2); }

    // Comparison
    bool operator==(const FruRecord& other) const { return fruData == other.fruData; }
    bool operator!=(const FruRecord& other) const { return fruData != other.fruData; }

    // Clear all fields
    void clear() { fruData.clear(); }

    // Number of fields
    size_t size() const { return fruData.size(); }
};

} // namespace iot1::config
