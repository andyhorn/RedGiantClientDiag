# Andy Horn
# November, 2019
# for Red Giant
# 
# Read the RLM client license file and test the TCP connections
# to the RLM server, outputting the results to the console
# window and to a text file.

import platform, os, socket, glob, sys

# Constants
WIN_LOCATION = "C:\\ProgramData\\Red Giant\\licenses\\"
MAC_LOCATION = "/Users/Shared/Red Giant/licenses/"
WEB_PORT_DEFAULT = 5054
OUTPUT_FILENAME = "results.txt"
SOCKET_TIMEOUT_SECONDS = 3

# Output formatting
OUTPUT_FORMAT = "%-18s%-10s%-10s"
HEADER = OUTPUT_FORMAT % ("Server", "Port", "Accessible")
BORDER = ''.join(['-' * len(HEADER)])

# Variables
ISV_PORT = None


# Class representing a TCP port
# Stores the IP/Hostname and port number
# Includes a method to test the connection and
# a boolean flag for its validity
class TcpPort:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.is_accessible = False

    def test(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT_SECONDS)
        try:
            sock.connect((self.address, int(self.port)))
            self.is_accessible = True
        except:
            self.is_accessible = False
        finally:
            sock.close()


class LicenseFile:
    def __init__(self, path):
        self.path = path
        self.ports = []
        self.host = ""
        self.in_correct_location = False
        self.correct_permissions = False

    def read(self):
        try:
            with open(self.path, 'r') as data:
                contents = data.readline().split(' ')
                self.host = contents[1].strip()
                port_num = contents[3].strip()
                cc_port = TcpPort(self.host, port_num)
                web_port = TcpPort(self.host, WEB_PORT_DEFAULT)
                self.ports.append(cc_port)
                self.ports.append(web_port)
                self.correct_permissions = True
                if ISV_PORT != 0 and ISV_PORT != None:
                    isv = TcpPort(self.host, ISV_PORT)
                    self.ports.append(isv)
                return True
        except IOError:
            return False


class OptionsFile:
    def __init__(self, path):
        self.path = path
        self.logging = False
        self.render_only = False
        self.errors = []
        self.in_correct_location = False
        self.correct_permissions = False

    def read(self):
        try:
            lines = []
            with open(self.path, 'r') as data:
                lines = data.readlines()
                self.correct_permissions = True
            for line in lines:
                if line.upper() == "REDGIANT_RENDER_ONLY=TRUE":
                    self.render_only = True
                elif line.upper() == "REDGIANT_ENTERPRISE_LOGGING=TRUE":
                    self.logging = True
                else:
                    if "REDGIANT_RENDER_ONLY" not in line.upper() and "REDGIANT_ENTERPRISE_LOGGING" not in line.upper():
                        self.errors.append("Unrecognized directive: %s" % line)
            return True
        except IOError:
            return False


# A logger class that will automatically write the output line
# to the console as well as appending it to a file, given by
# a filename argument upon instantiation
class Logger:
    def __init__(self, filename):
        self.filename = filename
        self.can_write = True

    def log(self, line):
        print(line)
        if self.can_write:
            try:
                with open(self.filename, 'a') as file:
                    file.write(line)
                    file.write("\n")
            except IOError:
                # Unable to open file, likely due to permissions
                self.can_write = False


# The main testing procedures wrapped into a class
# Some functionality is wrapped into the initialization
# while heavier functionality is wrapped into member methods
class TestEngine:
    def __init__(self):
        # Get the license directory path based on operating system
        self.dir_path = self.get_file_path(self)
        # Set the output (results.txt) license file path
        self.file = self.make_local_file_path(self, OUTPUT_FILENAME)
        # Instantiate a logger object with the given output file path
        self.logger = Logger(self.file)
        # Create an empty list to hold the LicenseFile objects
        self.licenses = []
        # Create an empty variable for an OptionsFile object
        self.options_files = []
        # Check if the license directory exists
        self.dir_exists = os.path.exists(self.dir_path)
        # If the directory exists, get the full contents, otherwise an empty list
        self.dir_contents = self.get_contents(self, self.dir_path) if self.dir_exists else []
        self.files_opened = False

    def list_files(self):
        d = self.get_file_path()
        contents = self.get_contents(d)
        return contents

    @staticmethod
    def get_contents(self, dir):
        contents = []
        for root, dirs, files in os.walk(dir):
            for f in files:
                contents.append("%s%s" % (root + os.path.sep if not root.endswith(os.path.sep) else root, f))
            for d in dirs:
                contents.extend(self.get_contents(self, d))
        return contents

    # If a "results.txt" file already exists, this will empty it
    # primarily for testing, but also helps keep things clean if
    # they run the script multiple times
    def init_file(self):
        try:
            # Open the file and clear its contents
            with open(self.file, 'w') as file:
                pass
        except IOError:
            # No permission to open the file, do nothing
            pass

    # Get this computer's hostname
    @staticmethod
    def get_client_hostname(self):
        return socket.gethostname()

    # Get the license directory path based on the current operating system
    @staticmethod
    def get_file_path(self):
        return WIN_LOCATION if platform.system().lower() == "windows" else MAC_LOCATION

    # Make the full path for a filename in the directory housing this script
    @staticmethod
    def make_local_file_path(self, filename):
        local_dir = sys.path[0]
        separator = os.path.sep
        full_filename = local_dir + separator + filename
        return full_filename

    # Scan the license files and instantiate TcpPort objects for
    # each file, along with a port for the web interface based
    # on the default port
    def read_license_files(self):
        # Set a flag to detect if no files were opened
        self.files_opened = False
        # Use glob to find all ".lic" files in the license directory
        license_files = filter(lambda p : '.lic' in p, self.dir_contents)
        # Loop through the license files that were found
        for license_file in license_files:
            file = LicenseFile(license_file)
            if file.read():
                self.files_opened = True
                correct_path = self.get_file_path(self)
                file.in_correct_location = self.get_file_location(self, license_file) + os.path.sep == correct_path
                self.licenses.append(file)

    # Look for the rlm options file and read its contents
    def read_options_file(self):
        options_files = filter(lambda p : 'rlm-options.txt' in p, self.dir_contents)
        for file in options_files:
            f = OptionsFile(file)
            correct_path = self.get_file_path(self)
            if self.get_file_location(self, file) + os.path.sep == correct_path:
                f.in_correct_location = True
            else:
                f.in_correct_location = False
            if f.read():
                self.options_files.append(f)

    # Call the test method on all ports that were found
    def test_ports(self):
        for lic in self.licenses:
            if lic.correct_permissions:
                for port in lic.ports:
                    port.test()

    @staticmethod
    def get_file_location(self, file):
        path = os.path.dirname(file)
        return path

    # Writes all the test results to the console and to the logger's file
    def write_results(self):
        self.logger.log("Thank you for using the Red Giant client-side diagnostic tool!")
        self.logger.log("Please contact volumesupport@redgiant.com if you have any questions or concerns.")
        self.logger.log("These test results have been written to %s" % self.file)
        self.logger.log('-' * 75)
        # Log the client hostname
        self.logger.log("\n\nClient hostname: %s" % self.get_client_hostname(self))
        # Log if the client license directory was present
        if self.dir_exists:
            self.logger.log("Licenses directory found!")
        else:
            self.logger.log("Licenses directory not found - Check the spelling and "
                            "location: %s" % self.get_file_path(self))
        # If the directory exists, log the rest of the results
        if self.dir_exists:
            # Log the contents of the directory
            self.logger.log("Directory contents:")
            self.logger.log('\n'.join(self.dir_contents))
            # If ports are present, log their test results
            if len(self.licenses) > 0:
                # Log the header and border line
                for lic in self.licenses:
                    self.logger.log("\nLicense file: %s" % lic.path)
                    if not lic.in_correct_location:
                        self.logger.log("This file is in the wrong location. To work properly, please move this file"
                                        " to %s" % self.get_file_path(self))
                    else:
                        self.logger.log("This file is in the correct location!")
                    if lic.correct_permissions:
                        self.logger.log("\nTest Results")
                        self.logger.log(HEADER)
                        self.logger.log(BORDER)
                        # Loop through the ports in the list and output their
                        # data and test results, piped through the formatter
                        for port in lic.ports:
                            self.logger.log(OUTPUT_FORMAT % (port.address, port.port, str(port.is_accessible)))
                        self.logger.log(BORDER)
                    else:
                        self.logger.log("Unable to open this file - Please check permissions")
            else:
                self.logger.log("No license files were found")
            if len(self.options_files):
                for options_file in self.options_files:
                    self.logger.log("\n\nRLM Options file found: %s" % options_file.path)
                    if not options_file.correct_permissions:
                        self.logger.log("Could not open this file - Please check permissions")
                    else:
                        if options_file.in_correct_location:
                            self.logger.log("This file is in the correct location!")
                        else:
                            self.logger.log("This file is not in the correct location. "
                                            "To work properly, please move it to %s" % self.get_file_path(self))
                        self.logger.log("Client logging enabled: %s" % options_file.logging)
                        self.logger.log("Render only enabled: %s" % options_file.render_only)
                        if len(options_file.errors):
                            self.logger.log("Errors:")
                            self.logger.log("\n".join(options_file.errors))

    # Drives the tests and logging methods
    def run_tests(self):
        self.logger.log("Running tests...\n")
        self.init_file()
        self.read_license_files()
        self.read_options_file()
        self.test_ports()
        self.write_results()


# Read any command line arguments
if (len(sys.argv) > 1):
    # Arguments exist
    port_num = 0
    try:
        port_num = int(sys.argv[1])
    except ValueError:
        pass
    finally:
        if port_num is not None:
            ISV_PORT = port_num
        else:
            ISV_PORT = 0

# Execute the script
tester = TestEngine()
tester.run_tests()
