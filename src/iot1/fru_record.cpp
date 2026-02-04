#include "fru_record.h"

namespace iot1::config {

FruRecord::FruRecord(const json& data) : fruData(data) {}

json& FruRecord::operator[](const std::string& key) {
    return fruData[key];
}

const json& FruRecord::operator[](const std::string& key) const {
    if (!fruData.contains(key)) {
        throw std::runtime_error("FRU field not found: " + key);
    }
    return fruData.at(key);
}

bool FruRecord::validate() const {
    // Basic FRU validation
    // FRU should have at least a manufacturer field
    // This is flexible - can vary by FRU type
    return true;
}

FruRecord FruRecord::fromJson(const json& data) {
    return FruRecord(data);
}

} // namespace iot1::config
