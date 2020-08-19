import numpy as np
from scipy import interpolate
import json
import csv
import os
import sys
import time

module_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(module_path)
from velocity_optimization.interface.Receiver import ZMQReceiver as Rec
from velocity_optimization.interface.Sender import ZMQSender as Snd


class VarPowerLimits:

    __slots__ = ('input_path',
                 '__s_var_pwr',
                 's_max_var_pwr',
                 '__P_var_pwr',
                 'f_pwr_intp',
                 'rec_recalc',
                 'snd_recalc')

    def __init__(self,
                 input_path: str):

        """
        Python version: 3.5
        Created by: Thomas Herrmann (thomas.herrmann@tum.de)
        Created on: 01.02.2020

        Documentation: Class to store and interpolate variable power limits to be used during driving to feed into the
        variable P_max constraint.

        Inputs:
        input_path: absolute path to folder containing variable vehicle and track information
        """

        self.input_path = input_path

        # s coordinate [m]
        self.__s_var_pwr = []
        # max. s coordinate [m]
        self.s_max_var_pwr = 0
        # max. power values [kW]
        self.__P_var_pwr = []

        with open(self.input_path + 'var_power_db.csv', newline='\n') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            for row in reader:
                self.__s_var_pwr = np.append(self.__s_var_pwr, json.loads(row[0]))
                self.__P_var_pwr = np.append(self.__P_var_pwr, json.loads(row[1]))

            # --- Postprocess variable power array (no negative values)
            self.__P_var_pwr[self.__P_var_pwr < 0] = 0

            self.s_max_var_pwr = np.max(self.__s_var_pwr)

            self.f_pwr_intp = interpolate.interp1d(self.__s_var_pwr, self.__P_var_pwr)

    def init_interface_recalc(self):

        # --- Initialize sender to trigger ESIM recalculation
        self.snd_recalc = Snd(theme='receiver_exp_esim')

        # --- Initialize receiver for information from ESIM
        self.rec_recalc = Rec(theme='sender_imp_vplanner')

        # Handshake with ESIM
        b_esim_ready = False
        while not b_esim_ready:

            rec_esim = self.rec_recalc.run()
            print("Handshake with ESIM:", rec_esim)

            if rec_esim is not None:

                # Acknowledge message with response
                self.snd_recalc.send(data=True)
                time.sleep(0.5)

                # Clear cache
                while self.rec_recalc.run() is not None:
                    pass

                # close and leave loop
                b_esim_ready = True


if __name__ == '__main__':

    vpl = VarPowerLimits(module_path + '/velocity_optimization/inputs/')
    print(vpl.f_pwr_intp([2, 3, 400]))

    # check ZMQ interfaces
    vpl.init_interface_recalc()
