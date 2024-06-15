import machine
import time

# 设置红外接收引脚
ir_pin = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)  # 加入上拉电阻

# NEC协议的脉冲时间（微秒）
NEC_HDR_MARK = 9000
NEC_HDR_SPACE = 4500
NEC_BIT_MARK = 560
NEC_ONE_SPACE = 1600
NEC_ZERO_SPACE = 560

# 允许的误差范围
TOLERANCE = 1000  # 最大容错范围，根据实际情况进行调整

# 用于捕获红外信号的脉冲时间戳
timestamps = []
last_timestamp = 0

# 定义按键和它们的红外码
key_codes = {
    '0': 0xff9867,
    '1': 0xffa25d,
    '2': 0xff629d,
    '3': 0xffe21d,
    '4': 0xff22dd,
    '5': 0xff02fd,
    '6': 0xffc23d,
    '7': 0xffe01f,
    '8': 0xffa857,
    '9': 0xff906f,
    '*': 0xff689f,
    '#': 0xffb04f,
    'UP': 0xff18f7,
    'LEFT': 0xff10ef,
    'OK': 0xff38c7,
    'RIGHT': 0xff5aa5,
    'DOWN': 0xff4ab5,
}

def ir_callback(pin):
    global timestamps, last_timestamp
    timestamp = time.ticks_us()
    if last_timestamp:
        pulse_length = time.ticks_diff(timestamp, last_timestamp)
        if pulse_length < 100000:  # 忽略过长的脉冲
            timestamps.append(pulse_length)
    last_timestamp = timestamp

# 初始化中断处理
ir_pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=ir_callback)

def match(value, target):
    return target - TOLERANCE < value < target + TOLERANCE  # 扩大容错范围

def decode_nec(pulses):
    if len(pulses) < 68:  # NEC编码大约需要68个脉冲（32位数据+2个引导+前导+结束脉冲）
        print("Not enough pulses:", len(pulses))
        return None

    # 解析数据
    if match(pulses[0], NEC_HDR_MARK) and match(pulses[1], NEC_HDR_SPACE):
        data = 0
        for i in range(2, 66, 2):
            if match(pulses[i], NEC_BIT_MARK):
                if match(pulses[i+1], NEC_ONE_SPACE):
                    data = (data << 1) | 1
                elif match(pulses[i+1], NEC_ZERO_SPACE):
                    data = (data << 1)
                else:
                    print("Pulse width error at index:", i+1, pulses[i+1])
                    return None
            else:
                print("Pulse width error at index:", i, pulses[i])
                return None

        # 检查结束脉冲
        if not match(pulses[-1], NEC_BIT_MARK):
            print("Invalid end pulse mark")
            return None

        return data
    else:
        print("Invalid header mark or space width:", pulses[0], pulses[1])
        return None

# 寻找最接近的按键码
def find_nearest_key(result):
    min_diff = float('inf')
    nearest_key = None
    
    for key, code in key_codes.items():
        diff = abs(result - code)
        if diff < min_diff:
            min_diff = diff
            nearest_key = key
            
    return nearest_key, min_diff

# 主循环
while True:
    if timestamps:
        pulses = timestamps[:]
        timestamps = []
        last_timestamp = 0  # 复位计时
        print("Received pulses:", pulses)  # 打印接收到的脉冲数据
        result = decode_nec(pulses)
        if result is not None:
            # 匹配最接近的按键
            matched_key, min_diff = find_nearest_key(result)
            if matched_key is not None:
                print("Received IR Code:", hex(result))
                print("Matched Key:", matched_key)
                print("Minimum Difference:", min_diff)
            else:
                print("Received IR Code:", hex(result))
                print("Unmatched Key")
        else:
            print("Failed to decode pulses")

    time.sleep(2)  # 增加延迟，避免过多的无效循环
