#include <iostream>
#include <string>
#include <cstring>
#include <unistd.h>
#include <signal.h>
#include <syslog.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <pwd.h>
#include <grp.h>

// Forward declarations
class PldmAgent {
public:
    PldmAgent() : running(false), daemonMode(false) {}
    
    int run(int argc, char* argv[]);
    void shutdown();
    bool isRunning() const { return running; }
    
private:
    bool running;
    bool daemonMode;
    
    int parseArgs(int argc, char* argv[]);
    int daemonize();
    void printUsage(const char* programName);
    static void signalHandler(int signum);
};

// Global instance for signal handler
static PldmAgent* g_pldmAgent = nullptr;

void PldmAgent::signalHandler(int signum) {
    if (g_pldmAgent) {
        g_pldmAgent->shutdown();
    }
}

void PldmAgent::printUsage(const char* programName) {
    std::cout << "Usage: " << programName << " [OPTIONS]\n\n"
              << "Options:\n"
              << "  -d, --daemon          Run as a daemon (default: foreground)\n"
              << "  -c, --config FILE     Configuration file (default: ./config.json)\n"
              << "  -l, --log-level LEVEL Log level: debug, info, warn, error, fatal\n"
              << "  -h, --help            Show this help message\n"
              << "  -v, --version         Show version information\n"
              << std::endl;
}

int PldmAgent::parseArgs(int argc, char* argv[]) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "-d" || arg == "--daemon") {
            daemonMode = true;
        } else if (arg == "-c" || arg == "--config") {
            if (++i >= argc) {
                std::cerr << "Error: --config requires an argument\n";
                return 1;
            }
            // TODO: Store config file path
        } else if (arg == "-l" || arg == "--log-level") {
            if (++i >= argc) {
                std::cerr << "Error: --log-level requires an argument\n";
                return 1;
            }
            // TODO: Set log level
        } else if (arg == "-h" || arg == "--help") {
            printUsage(argv[0]);
            return 2;  // Special code: exit successfully after printing help
        } else if (arg == "-v" || arg == "--version") {
            std::cout << "PLDM Agent version 1.0.0\n";
            return 2;  // Special code: exit successfully after printing version
        } else {
            std::cerr << "Error: Unknown option '" << arg << "'\n";
            printUsage(argv[0]);
            return 1;
        }
    }
    return 0;
}

int PldmAgent::daemonize() {
    // Fork off the parent process
    pid_t pid = fork();
    if (pid < 0) {
        std::cerr << "Error: Failed to fork process\n";
        return 1;
    }
    
    // Exit the parent process
    if (pid > 0) {
        exit(0);
    }
    
    // Create a new session and become session leader
    if (setsid() < 0) {
        std::cerr << "Error: Failed to create new session\n";
        return 1;
    }
    
    // Change working directory to root to avoid holding a directory open
    if (chdir("/") < 0) {
        std::cerr << "Error: Failed to change working directory\n";
        return 1;
    }
    
    // Redirect standard file descriptors
    int fd = open("/dev/null", O_RDWR);
    if (fd < 0) {
        std::cerr << "Error: Failed to open /dev/null\n";
        return 1;
    }
    
    dup2(fd, STDIN_FILENO);
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);
    
    if (fd > 2) {
        close(fd);
    }
    
    // Open syslog
    openlog("pldm-agent", LOG_PID | LOG_NDELAY, LOG_DAEMON);
    
    return 0;
}

int PldmAgent::run(int argc, char* argv[]) {
    // Parse command line arguments
    int parseResult = parseArgs(argc, argv);
    if (parseResult != 0) {
        return (parseResult == 2) ? 0 : 1;  // 2 = help/version printed, exit cleanly
    }
    
    // Daemonize if requested
    if (daemonMode) {
        if (daemonize() != 0) {
            return 1;
        }
    }
    
    // Set up signal handlers
    g_pldmAgent = this;
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    signal(SIGHUP, signalHandler);
    
    // Log startup
    if (daemonMode) {
        syslog(LOG_INFO, "PLDM Agent starting (daemon mode)");
    } else {
        std::cout << "PLDM Agent starting (foreground mode)\n";
    }
    
    running = true;
    
    // TODO: Initialize agent
    // TODO: Load configuration
    // TODO: Initialize MCTP transport
    // TODO: Start main event loop
    
    // Placeholder: simulate work
    while (running) {
        sleep(1);
    }
    
    // TODO: Cleanup
    if (daemonMode) {
        syslog(LOG_INFO, "PLDM Agent shutting down");
        closelog();
    } else {
        std::cout << "PLDM Agent shutting down\n";
    }
    
    return 0;
}

void PldmAgent::shutdown() {
    running = false;
}

int main(int argc, char* argv[]) {
    PldmAgent agent;
    return agent.run(argc, argv);
}
