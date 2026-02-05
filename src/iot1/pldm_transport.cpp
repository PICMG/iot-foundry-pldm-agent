#include "iot1/protocol/pldm_transport.h"

namespace iot1::protocol {

PldmTransport::PldmTransport() : local_eid(0) {}

PldmTransport::~PldmTransport() {
    if (running) {
        close();
    }
}

bool PldmTransport::initialize(const std::string& mctp_interface,
                               uint8_t local_id,
                               const std::vector<uint8_t>& peer_eids) {
    try {
        mctp = std::make_unique<LinuxMctpSerial>();
        std::string result = mctp->initialize(mctp_interface, local_id, peer_eids);
        
        if (!result.empty()) {
            std::cerr << "MCTP initialization failed: " << result << std::endl;
            return false;
        }
        
        local_eid = local_id;
        running = true;
        
        // Start receive thread
        rx_thread = std::thread(&PldmTransport::receiveLoop, this);
        
        // Start timeout cleanup thread
        timeout_thread = std::thread(&PldmTransport::timeoutCleanupLoop, this);
        
        std::cout << "PldmTransport initialized: local_eid=" << (int)local_eid 
                  << ", interface=" << mctp_interface << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "PldmTransport initialization exception: " << e.what() << std::endl;
        return false;
    }
}

void PldmTransport::close() {
    running = false;
    
    // Wait for threads to finish
    if (rx_thread.joinable()) {
        rx_thread.join();
    }
    if (timeout_thread.joinable()) {
        timeout_thread.join();
    }
    
    if (mctp) {
        mctp->close();
    }
    
    // Clean up any pending requests
    {
        std::lock_guard<std::mutex> lock(pending_lock);
        for (auto& [inst_id, pending_req] : pending) {
            try {
                pending_req.response_promise.set_exception(
                    std::make_exception_ptr(
                        std::runtime_error("Transport closing")
                    )
                );
            } catch (...) {
                // Already satisfied
            }
        }
        pending.clear();
    }
}

uint8_t PldmTransport::allocateInstanceId() {
    // Atomic increment - no lock needed
    // Instance ID is 6 bits (0-63), but PLDM typically uses 5 bits (0-31)
    uint8_t id = (next_instance_id++) % 32;
    return id;
}

void PldmTransport::receiveLoop() {
    while (running) {
        try {
            std::vector<uint8_t> msg;
            
            // Receive from MCTP (non-blocking with timeout)
            ssize_t recv_len = mctp->receive(msg);
            if (recv_len <= 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                continue;
            }
            
            if (msg.size() < 2) {
                std::cerr << "Received message too short: " << msg.size() << " bytes" << std::endl;
                continue;
            }
            
            // Extract instance ID from PLDM header (byte 0, bits 2-6)
            // PLDM header: [response(7) | reserved(6) | instance_id(5-2) | reserved(1-0)]
            uint8_t instance_id = (msg[0] >> 2) & 0x1F;  // 5 bits = 0-31
            
            {
                // LOCK: Acquire mutex before accessing pending map
                std::lock_guard<std::mutex> lock(pending_lock);
                
                // Find matching pending request
                auto it = pending.find(instance_id);
                if (it != pending.end()) {
                    // Found! Deliver response to waiting endpoint
                    try {
                        it->second.response_promise.set_value(msg);
                    } catch (const std::future_error& e) {
                        std::cerr << "Failed to set promise for instance_id " 
                                  << (int)instance_id << ": " << e.what() << std::endl;
                    }
                    // Remove from pending
                    pending.erase(it);
                } else {
                    // Response for unknown instance ID
                    std::cerr << "Received response for unknown instance_id: " 
                              << (int)instance_id << std::endl;
                    // Could implement orphan response queue for debugging
                }
            }
            // UNLOCK: mutex released automatically
            
        } catch (const std::exception& e) {
            std::cerr << "ReceiveLoop exception: " << e.what() << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
}

void PldmTransport::timeoutCleanupLoop() {
    while (running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        auto now = std::chrono::steady_clock::now();
        
        {
            std::lock_guard<std::mutex> lock(pending_lock);
            
            auto it = pending.begin();
            while (it != pending.end()) {
                if (now > it->second.timeout) {
                    // This request has timed out
                    try {
                        it->second.response_promise.set_exception(
                            std::make_exception_ptr(
                                std::runtime_error("PLDM request timeout")
                            )
                        );
                    } catch (const std::future_error& e) {
                        // Already satisfied (response arrived just in time)
                    }
                    
                    std::cerr << "Request timeout for instance_id: " << (int)it->first 
                              << ", target_eid: " << (int)it->second.target_eid << std::endl;
                    it = pending.erase(it);
                } else {
                    ++it;
                }
            }
        }
    }
}

std::future<std::vector<uint8_t>> PldmTransport::sendAsync(
    uint8_t target_eid,
    const std::vector<uint8_t>& request,
    int timeout_ms) {
    
    if (request.empty()) {
        auto promise = std::make_shared<std::promise<std::vector<uint8_t>>>();
        promise->set_exception(std::make_exception_ptr(
            std::invalid_argument("Empty request message")
        ));
        return promise->get_future();
    }
    
    // Extract instance ID from request header (byte 0, bits 2-6)
    uint8_t instance_id = (request[0] >> 2) & 0x1F;
    
    // Create pending request structure
    PendingRequest pending_req{
        std::promise<std::vector<uint8_t>>(),
        std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms),
        target_eid
    };
    
    // Get future before moving promise
    auto future = pending_req.response_promise.get_future();
    
    {
        // LOCK: Register pending request BEFORE sending
        // This ensures if response arrives immediately, promise is already ready
        std::lock_guard<std::mutex> lock(pending_lock);
        
        // Check for instance ID collision (should be rare with proper allocation)
        if (pending.find(instance_id) != pending.end()) {
            std::cerr << "Warning: Instance ID collision " << (int)instance_id 
                      << " (max 32 concurrent requests). Overwriting." << std::endl;
        }
        
        pending[instance_id] = std::move(pending_req);
    }
    // UNLOCK: mutex released
    
    // SEND AFTER promise is registered
    try {
        mctp->send(request);
    } catch (const std::exception& e) {
        std::cerr << "Send failed for instance_id " << (int)instance_id 
                  << ": " << e.what() << std::endl;
        
        // Remove the pending request and set exception
        {
            std::lock_guard<std::mutex> lock(pending_lock);
            auto it = pending.find(instance_id);
            if (it != pending.end()) {
                try {
                    it->second.response_promise.set_exception(
                        std::make_exception_ptr(std::runtime_error("Send failed"))
                    );
                } catch (const std::future_error&) {
                    // Already satisfied
                }
                pending.erase(it);
            }
        }
    }
    
    return future;
}

bool PldmTransport::sendAndWaitResponse(
    uint8_t target_eid,
    const std::vector<uint8_t>& request,
    std::vector<uint8_t>& response,
    int timeout_ms) {
    
    auto future = sendAsync(target_eid, request, timeout_ms);
    
    try {
        response = future.get();  // Blocks until response or timeout
        return true;
    } catch (const std::future_error& e) {
        std::cerr << "Future error: " << e.what() << std::endl;
        return false;
    } catch (const std::exception& e) {
        std::cerr << "Request error: " << e.what() << std::endl;
        return false;
    }
}

int PldmTransport::getPendingRequestCount() const {
    std::lock_guard<std::mutex> lock(pending_lock);
    return pending.size();
}

}  // namespace iot1::protocol
