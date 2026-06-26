from pylimo import limo
import time


limo = limo.LIMO()
limo.EnableCommand()

while True:
    limo.SetMotionCommand(linear_vel=0.1,angular_vel=-0.01)
    time.sleep(0.1)
    