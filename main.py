"""
Text below is copied from "Using a Control Program in Maxwell 2D and 3D
Transient Solutions" in Maxwell Help.
The process can be summarized as:
1. The transient solver reads control parameters from user.ctl.
2. The transient solver solves the current time step.
3. The transient solver copies the previous solution to previous.ctl and writes
 out solution information to solution.ctl.
4. The transient solver calls the user control program.
5. The user-control program writes control information to file user.ctl.
6. Return to the transient solver if the control program succeeds with exit
status 0 or fails with exit status non-zero.
7. Return to step 1 for the next time step.

python version is 3.7.8 in ANSYS Electronics 2021R1
可以使用numpy、scipy和matplotlib
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

log_path = Path.home() / 'Desktop/controlProgram'  # log文件夹放在桌面
log_path.mkdir(parents=True, exist_ok=True)  # 建立log文件夹，如果不存在就新建
logger = logging.getLogger()  # 以下几行都是logger输出参数
hdlr = logging.FileHandler(
    log_path / datetime.now().strftime('control-%Y-%m-%d.log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)
try:
    user_paths = os.environ['PYTHONPATH'].split(os.pathsep)
except KeyError:
    user_paths = []
logger.info(f'{os.path.dirname(sys.executable)}')
"""
下面是激励的输出模板，不要随便修改
参数：
name:
windingSrc: 绕组数值，可以是电压源或者电流源，仅仅是数值，单位为A（电压源）或者V（电流源）
windingR:   绕组电阻，单位为欧姆（Ohm），电压源时使用
windingL:   绕组端部电感，单位为亨利（H），电压源时使用
"""
excitation_template = 'windingSrc {name} {windingSrc}\n' \
                      'windingR {name} {windingR}\n' \
                      'windingL {name} {windingL}\n'

"""
下面是自定义参数，全局变量，在程序运行时使用。
"""
current_density = 8  # unit is A/mm2
slot_size = 10  # unit is mm2
fill_factor = 0.5
turns = 29
irms = current_density * slot_size * fill_factor / turns
imax = irms * np.sqrt(2)
pole = 2
speed = 120000  # speed unit is RPM
freq = pole / 2 * speed / 60  # freq = pole pair * (speed in rpm) / 60
phase = 3


def write_user_file(sol, user_file_name='user.ctl', mode='w'):
    """
    写入控制文件函数
    :param sol: 模型的解， 来自于load_solution_file函数
    :param user_file_name: 默认值为"user.ctl"，不要随意修改
    :param mode: 写入模式，不要随意修改，默认为'w'
    :return: 空
    """
    output = 'begin_data\n'

    # 获取时间
    t = float(sol['time'])

    # 添加时间
    output += f'time {t}\n'
    if t != -1:
        # 获取每个绕组的名称
        winding_names = sol['windingEmf'].keys()

        # 每相激励的计算
        excitations = [
            imax * np.sin(2 * np.pi * freq * t - phase_angle * 2 / 3 * np.pi)
            for
            phase_angle in range(phase)]

        # 将每相激励写入output
        for name, excitation in zip(winding_names, excitations):
            output += excitation_template.format(name=name,
                                                 windingSrc=excitation,
                                                 windingR=0.1,
                                                 windingL=0.001)
    output += 'end_data\n'

    # 将输出写入控制文件供求解器读取
    with open(user_file_name, mode) as user_file:
        user_file.write(output)

    logger.info(output)


def load_solution_file(solution_filenname='solution.ctl'):
    """
    读取求解器的输出的函数
    :param solution_filenname: 求解器的输出文件名，默认值为'solution.ctl'，不要随意修改
    :return:
    """
    files = Path().glob('*.ctl')
    logger.info(f'ctl files = {list(files)}')
    solution_filepath = Path(solution_filenname)
    sol = {}
    # 一开始没有输出文件，所以需要判断。如果输出文件不存在则新建一个空白文件
    if solution_filepath.exists():
        # 以只读方式打开求解器输出的文件，将其解析成一个字典
        with solution_filepath.open('r') as solution_file:
            data = solution_file.readlines()

            for line in data:
                split_line = line.strip().split()
                key = split_line[0]
                if len(split_line) > 2:
                    if key not in sol:
                        sol[key] = {
                            split_line[1]: split_line[2]}
                    else:
                        sol[key][split_line[1]] = split_line[2]
                elif len(split_line) == 2:
                    value = split_line[1]
                    sol[key] = value
        logger.info(''.join(data))

    else:
        logger.info('solution file does not exist, create user.ctl')
        sol['time'] = -1
        # with open('user.ctl', 'w') as f:
        #     f.write('begin_data\nend_data\n')
    return sol


# 运行
if __name__ == '__main__':
    solution = load_solution_file()
    write_user_file(solution)
    # step 6. Return to the transient solver if the control program succeeds
    # with exit status 0 or fails with exit status non-zero.
    sys.exit(0)
