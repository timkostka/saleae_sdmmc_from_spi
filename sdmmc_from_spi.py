"""
High Level Analyzer script for interpreting SDMMC communication.

This is supported by Saleae Logic v2.3.1 or later.

For more information, see https://github.com/saleae/logic2-examples

To set up, create an SPI analyzer with the SDIO_CK signal on the SPI_MOSI line
and use that channel as the input for this analyzer.

This analyzer will only decode the CMD signal.  The data signal(s) are not
monitored.

Author: Tim Kostka <kostka@gmail.com>
Website: https://github.com/timkostka/saleae_sdmmc_from_spi

"""


from saleae.data.timing import GraphTimeDelta
from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame


# states (CURRENT_STATE)
CURRENT_STATE = {
    0: "IDLE",
    1: "READY",
    2: "IDENTIFICATION",
    3: "STANDBY",
    4: "TRANSFER",
    5: "DATA",
    6: "RECEIVE",
    7: "PROGRAMMING",
    8: "DISCONNECT",
    9: "BUS TEST",
    10: "SLEEP",
}

# command value info
# tuple is (name, response)
# response of 0 means no response
COMMAND_INFO = {
    # Basic commands (class 0 and class 1)
    0: ("GO_IDLE_STATE", None),
    1: ("SEND_OP_COND", 3),
    2: ("ALL_SEND_CID", 2),
    3: ("SET_RELATIVE_ADDR", 1),
    4: ("SET_DSR", None),
    5: ("SLEEP_AWAKE", 1),
    6: ("SWITCH", 1),
    7: ("SELECT_CARD", 1),
    8: ("SEND_EXT_CSD", 1),
    9: ("SEND_CSD", 2),
    10: ("SEND_CID", 2),
    11: ("obsolete", None),
    12: ("STOP_TRANSMISSION", 1),
    13: ("SEND_STATUS", 1),
    14: ("BUSTEST_R", 1),
    15: ("GO_INACTIVE_STATE", None),
    19: ("BUSTEST_W", 1),
    # Block-oriented read commands (class 2)
    16: ("SET_BLOCKLEN", 1),
    17: ("READ_SINGLE_BLOCK", 1),
    18: ("READ_MULTIPLE_BLOCK", 1),
    21: ("SEND_TUNING_BLOCK", 1),
    # Class 3 commands
    20: ("obsolete", None),
    22: ("reserved", None),
    # Block-oriented write commands (class 4)
    23: ("SET_BLOCK_COUNT", 1),
    24: ("WRITE_BLOCK", 1),
    25: ("WRITE_MULTIPLE_BLOCK", 1),
    26: ("PROGRAM_CID", 1),
    27: ("PROGRAM_CSD", 1),
    49: ("SET_TIME", 1),
    # Block-oriented write protection commands (class 6)
    28: ("SET_WRITE_PROT", 1),
    29: ("CLR_WRITE_PROT", 1),
    30: ("SEND_WRITE_PROT", 1),
    31: ("SEND_WRITE_PROT_TYPE", 1),
    # Erase commands (class 5)
    35: ("ERASE_GROUP_START", 1),
    36: ("ERASE_GROUP_END", 1),
    38: ("ERASE", 1),
    # I/O mode commands (class 9)
    39: ("FAST_IO", 4),
    40: ("GO_IRQ_STATE", 5),
    # Lock Device commands (class 7)
    42: ("LOCK_UNLOCK", 1),
    # Application-specific commands (class 8)
    55: ("APP_CMD", 1),
    56: ("GEN_CMD", 1),
    # Security Protocols (class 1None)
    52: ("IO_RW_DIRECT", 5),
    53: ("IO_RW_EXTENDED", 5),
    54: ("PROTOCOL_WR", 1),
    # Command Queues (class 11)
    44: ("QUEUED_TASK_PARAMS", 1),
    45: ("QUEUED_TASK_ADDRESS", 1),
    46: ("EXECUTE_READ_TASK", 1),
    47: ("EXECUTE_WRITE_TASK", 1),
    48: ("CMDQ_TASK_MGMT", 1),
}


def get_response_length(resp):
    """Return the length of the given response type."""
    return 136 if resp == 2 else 48


def get_command_name(cmd):
    """Return the command name from the command value."""
    if cmd in COMMAND_INFO:
        return COMMAND_INFO[cmd][0]
    return "unknown"


def get_command_response(cmd):
    """Return the response type from the given command value."""
    if cmd in COMMAND_INFO:
        return COMMAND_INFO[cmd][1]
    return None


def bits_from_byte(value):
    """"Return the bits from the byte."""
    return [bool(value & bit) for bit in [128, 64, 32, 16, 8, 4, 2, 1]]


def value_from_bits(bits):
    """Return an integer value given its bits."""
    value = 0
    for x in bits:
        value *= 2
        if x:
            value += 1
    return value


def interpret_command(self, bits):
    """Return a string description from the command bits."""
    assert len(bits) == 48
    okay = True
    start_bit = bits[0]
    transmission_bit = bits[1]
    command_index = value_from_bits(bits[2:8])
    argument = value_from_bits(bits[8:40])
    crc7 = value_from_bits(bits[40:47])
    end_bit = value_from_bits(bits[47:48])
    if start_bit or not transmission_bit or not end_bit:
        okay = False
    if command_index in COMMAND_INFO:
        info = get_command_name(command_index) + " (CMD%d)" % command_index
    else:
        info = "CMD%d" % command_index
    if command_index == 52:
        #Argument start at position 8
        rw_flag = bits[8]
        function = value_from_bits(bits[9:12])
        raw_flag = bits[12]
        reg_address = value_from_bits(bits[14:31])
        if rw_flag == 1:
            write_data = value_from_bits(bits[32:40])
            info += ": Write: %d" % write_data
        else:
            info += ": Read"
        info += " Func%d" % function
        info += ", Address 0x%x" % reg_address
    elif command_index == 53:
        rw_flag = bits[8]
        function = value_from_bits(bits[9:12])
        block_mode = bits[12]
        op_code = bits[13]
        reg_address = value_from_bits(bits[14:31])
        byte_block_cnt = value_from_bits(bits[31:40])
        if rw_flag == 1:
            info += ": Write" 
        else:
            info += ": Read"
        info += " Func%d" % function
        if op_code == 1:
            info += ", Inc Address 0x%x" % reg_address
        else:
            info += ", Fix Address 0x%x" % reg_address
        if block_mode == 1:
            info += ", BlockMode:"
            info += " %d blocks" % byte_block_cnt
            
            # number of bytes to skip from to log, data block + CRC
            self.cdm53_skip_next_bytes = self.cdm53_block_size_length + 2
            # number of blocks to read/write, and reset received ones
            self.cmd53_blocks_pending = byte_block_cnt
            self.cmd53_blocks_received = 0
        else:
            info += ", ByteMode:"
            info += " %d bytes" % byte_block_cnt

            # number of bytes to skip from to log, received in the command + CRC
            self.cdm53_skip_next_bytes = byte_block_cnt + 2
            # number of blocks to read/write
            self.cmd53_blocks_pending = 1 #byte mode, only 1 block always, and reset received ones
            self.cmd53_blocks_received = 0
    else:    
        info += ", arg:%d" % argument
    if not okay:
        info += ", ERROR"
    return info


def interpret_response1(bits):
    """Return a string description from the response 1 bits."""
    assert len(bits) == 48
    okay = True
    start_bit = bits[0]
    transmission_bit = bits[1]
    command_index = value_from_bits(bits[2:8])
    device_status = bits[8:40]
    crc7 = value_from_bits(bits[40:47])
    end_bit = value_from_bits(bits[47:48])
    if start_bit or transmission_bit or not end_bit:
        okay = False
    current_state = value_from_bits(device_status[19:23])
    info = "R1, "
    if current_state in CURRENT_STATE:
        info += CURRENT_STATE[current_state]
    else:
        info += "UNKNOWN (%d)" % current_state
        okay = False
    # add error flags
    if device_status[0]:
        info += " ADDRESS_OUT_OF_RANGE"
    if device_status[1]:
        info += " ADDRESS_MISALIGN"
    if device_status[2]:
        info += " BLOCK_LEN_ERROR"
    if device_status[3]:
        info += " ERASE_EQ_ERROR"
    if device_status[4]:
        info += " ERASE_PARAM"
    if device_status[5]:
        info += " WP_VIOLATION"
    if device_status[6]:
        info += " DEVICE_IS_LOCKED"
    if device_status[7]:
        info += " LOCK_UNLOCK_FAILED"
    if device_status[8]:
        info += " COM_CRC_ERROR"
    if device_status[9]:
        info += " ILLEGAL_COMMAND"
    if device_status[10]:
        info += " DEVICE_ECC_FAILED"
    if device_status[11]:
        info += " CC_ERROR"
    if device_status[12]:
        info += " ERROR"
    return info


def interpret_response2(bits):
    """Return a string description from the response 2 bits."""
    assert len(bits) == 136
    return r"R2, CID or CSD"
    okay = True
    start_bit = bits[0]
    transmission_bit = bits[1]
    command_index = value_from_bits(bits[2:8])
    device_status = bits[8:40]
    crc7 = value_from_bits(bits[40:47])
    end_bit = value_from_bits(bits[47:48])
    if start_bit or transmission_bit or not end_bit:
        okay = False
    current_state = value_from_bits(device_status[19:23])
    info = "R1, "
    if current_state in CURRENT_STATE:
        info += CURRENT_STATE[current_state]
    else:
        info += "UNKNOWN (%d)" % current_state
        okay = False
    if not okay:
        info += ", ERROR"
    return info


def interpret_response3(bits):
    """Return a string description from the response 3 bits."""
    assert len(bits) == 48
    okay = True
    start_bit = bits[0]
    transmission_bit = bits[1]
    check_bits_1 = bits[2:8]
    ocr_register = bits[8:40]
    check_bits_2 = bits[40:47]
    end_bit = value_from_bits(bits[47:48])
    info = "R3, %s" % ("READY" if ocr_register[0] else "BUSY")
    return info

def interpret_response5(bits):
    """Return a string description from the response 3 bits."""
    info = "R5"
    return info

class SdioState:
    def __init__(self):
        # bits leftover for the next command or response
        self.command_bits = []
        # start_time of the start of the command bits
        self.command_start = None
        # value used during debugging
        self.debug = None
        # time of first value
        self.first_time = None
        # response number expected, or None
        self.expected_response = None
        # bits in the expected response
        self.expected_response_length = 48
        # configuration of the block length during CMD53
        self.cdm53_block_size_length = 256
        # number of bytes pending to skip from the CMD53 block transmission
        self.cdm53_skip_next_bytes = 0
        # number of blocks pending to transmit in multiblock requests
        self.cmd53_blocks_pending = 0
        # flag to know when block has started
        self.cmd53_start_token_received = 0
        # start_time of the block data
        self.cmd53_data_start = None
        # number of blocks already received, just for printf
        self.cmd53_blocks_received = 0
        print("\n\n\n\n\n")

    def add_byte(self, value, start_time, end_time):
        """
        Add a byte of data and return a command, or None.

        start is the start time of the byte
        end is the end time of the byte

        """
        if isinstance(value, bytes):
            assert len(value) == 1
            value = value[0]
        assert isinstance(value, int)
        
        ################### CMD53 handling #########################
        # Is CMD53 block received and data processing pending?
        if (self.cdm53_skip_next_bytes > 0):
            # Is Start Block Token recevied?
            if (self.cmd53_start_token_received == 0):
                if ((value == 0xFC) or (value == 0xFD)):
                    self.cmd53_start_token_received = 1
                    #data = {
                    #    "start_time": start_time,
                    #    "end_time": end_time,
                    #    "info": "START_TOKEN",
                    #}
                    #return data
                    print("---> START_TOKEN CMD53")
                    self.cmd53_data_start = end_time
                    return None
                else:
                    return None
            else:
                # Start Token already received, let's skipt the bytes, part of CMD53 write data
                if self.cdm53_skip_next_bytes > 1:
                    self.cdm53_skip_next_bytes -= 1
                    return None
                else:
                    #last byte of the block received, check for blocks
                    self.cmd53_blocks_pending -= 1
                    self.cmd53_blocks_received += 1
                    info = "DATA BLOCK %d" % self.cmd53_blocks_received
                    if self.cmd53_blocks_pending == 0:
                        #CMD53 finished...
                        self.cdm53_skip_next_bytes = 0
                        self.cmd53_start_token_received = 0
                        print("---> END CMD53")
                        data = {
                            "start_time": self.cmd53_data_start,
                            "end_time": end_time,
                            "info": info,
                        }
                        return data
                    else:
                        #prepare to receve next block
                        self.cdm53_skip_next_bytes = self.cdm53_block_size_length + 2
                        self.cmd53_start_token_received = 0
                        print("---> END BLOCK")
                        data = {
                            "start_time": self.cmd53_data_start,
                            "end_time": end_time,
                            "info": info,
                        }
                        return data

        # if bus is idle, ignore value
        if value == 255 and not self.command_bits:
            return None
        if not self.first_time:
            self.first_time = start_time
        new_bits = bits_from_byte(value)
        bit_length = GraphTimeDelta(float(end_time - start_time) / 7.5)
        # self.debug = "t %s to %s" % (start_time, end_time)
        self.debug = "start_time:%s, end_time:%s" % (start_time, end_time)
        # if we're expecting a response, look for one
        # self.debug = "start %g" % (end_time - start_time)
        # start_time -= bit_length * 1.5
        # start_time -= 1e-7

        # start of new command
        if not self.command_bits:
            count = 0
            while new_bits[0]:
                count += 1
                del new_bits[0]
            self.command_start = start_time + GraphTimeDelta(count * float(bit_length))
            self.command_bits = new_bits
            return None
        # add bits to command
        self.command_bits += new_bits
        # if not enough to complete a command, just return
        if len(self.command_bits) < self.expected_response_length:
            return None
        # if we reached this point, we have a response or a command
        this_response_length = self.expected_response_length
        this_response_type = self.expected_response
        # get end time of this
        command_start = self.command_start
        command_end = end_time - GraphTimeDelta(float(bit_length) * (
            len(self.command_bits) - this_response_length
        ))
        bits = self.command_bits[:this_response_length]
        print("\n")
        print("".join("1" if x else "0" for x in bits))
        # determine if response or command
        transmission_bit = bits[1]
        if transmission_bit:
            info = interpret_command(self,bits)
            command_index = value_from_bits(bits[2:8])
            # if a command, set up the next expected response
            self.expected_response = get_command_response(command_index)
            self.expected_response_length = get_response_length(
                self.expected_response
            )
        else:
            if this_response_type == 1 or this_response_type is None:
                info = interpret_response1(bits)
            elif this_response_type == 2:
                info = interpret_response2(bits)
            elif this_response_type == 3:
                info = interpret_response3(bits)
            elif this_response_type == 5:
                info = interpret_response5(bits)
            else:
                print("Unknown response type")
                info = "R%s" % this_response_type
            self.expected_response = None
            self.expected_response_length = 48
        # TODO: figure this out, expected_response_length is reset above
        # see if new command is started within this byte
        self.command_bits = self.command_bits[this_response_length:]
        if all(x for x in self.command_bits):
            self.command_bits = None
        else:
            while self.command_bits[0]:
                del self.command_bits[0]
            self.command_start = end_time
            self.command_start -= GraphTimeDelta(float(bit_length) * (len(self.command_bits) - 0.5))
            print("new command bits =", self.command_bits)
        print(info)
        print(
            "start=%s, duration=%s"
            % (command_start, command_end - command_start)
        )
        data = {
            "start_time": command_start,
            "end_time": command_end,
            "info": info,
        }
        return data


class SdmmcFromSpiAnalyzer(HighLevelAnalyzer):

    result_types = {
        "error": {"format": "ERROR"},
        "sdio": {"format": "{{data.info}}"},
    }

    def __init__(self):
        self.state = SdioState()

    def decode(self, data):
        if not "mosi" in data.data:
            return
        info = self.state.add_byte(
            data.data["mosi"], data.start_time, data.end_time
        )
        if info:
            return AnalyzerFrame(
                'sdio',
                info["start_time"],
                info["end_time"],
                {"info": info["info"]}
            )
