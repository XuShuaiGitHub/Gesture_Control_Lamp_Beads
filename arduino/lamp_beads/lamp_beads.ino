const int pinR = 9;  // 红色通道PWM引脚
const int pinG = 10; // 绿色通道PWM引脚
const int pinB = 11; // 蓝色通道PWM引脚

int currentR = 128;    // 初始红色亮度（0~255，默认灰色）
int currentG = 128;    // 初始绿色亮度
int currentB = 128;    // 初始蓝色亮度
bool isLocked = false; // 初始为「解锁」状态（false=解锁，true=锁定）

void setup()
{
    Serial.begin(9600);    // 初始化串口（与Python端波特率一致）
    pinMode(pinR, OUTPUT); // 将RGB引脚设为输出模式
    pinMode(pinG, OUTPUT);
    pinMode(pinB, OUTPUT);

    // 初始化PWM输出（默认显示灰色）
    analogWrite(pinR, currentR);
    analogWrite(pinG, currentG);
    analogWrite(pinB, currentB);
}

void loop()
{
    if (Serial.available() > 0)
    {                                               // 检查串口是否有新指令
        String line = Serial.readStringUntil('\n'); // 读取一行指令（Python用\n结尾）
        line.trim();                                // 去除字符串首尾的空格/换行符

        // 拆分指令：格式为 "R,G,B,锁定状态"（例如 "255,0,0,1" 表示红色+锁定）
        int comma1 = line.indexOf(',');             // 第一个逗号位置
        int comma2 = line.indexOf(',', comma1 + 1); // 第二个逗号
        int comma3 = line.indexOf(',', comma2 + 1); // 第三个逗号

        // 确保指令格式正确（有3个逗号，分割出4个值）
        if (comma1 != -1 && comma2 != -1 && comma3 != -1)
        {
            // 提取R、G、B、锁定状态
            int r = line.substring(0, comma1).toInt();          // 红色通道值
            int g = line.substring(comma1 + 1, comma2).toInt(); // 绿色通道值
            int b = line.substring(comma2 + 1, comma3).toInt(); // 蓝色通道值
            bool newLock = line.substring(comma3 + 1).toInt();  // 新的锁定状态（0=解锁，1=锁定）

            // 锁定逻辑：仅「解锁」时更新颜色；「锁定」时保持当前颜色
            if (!isLocked)
            {
                currentR = r; // 解锁时，更新红色亮度
                currentG = g; // 解锁时，更新绿色亮度
                currentB = b; // 解锁时，更新蓝色亮度
            }
            isLocked = newLock; // 同步锁定状态（无论是否解锁，状态要和Python端一致）

            // 输出PWM信号，控制RGB灯
            analogWrite(pinR, currentR);
            analogWrite(pinG, currentG);
            analogWrite(pinB, currentB);

            // 串口回显（调试用，可删除）
            Serial.print("当前颜色：R=");
            Serial.print(currentR);
            Serial.print(", G=");
            Serial.print(currentG);
            Serial.print(", B=");
            Serial.print(currentB);
            Serial.print(", 锁定状态=");
            Serial.println(isLocked);
        }
    }
}