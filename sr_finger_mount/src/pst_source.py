#!/usr/bin/env python3

# Copyright 2021 Shadow Robot Company Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from sr_robot_msgs.msg import ShadowPST
import numpy as np
import rospy


if __name__ == "__main__":

    rospy.init_node("pst_source_node")
    pub = rospy.Publisher("rh/tactile", ShadowPST, queue_size=1)
    msg = ShadowPST()
    time = 0

    while not rospy.is_shutdown():
        pressure_th = int(np.sin(time)*100)+100
        pressure_ff = int(np.sin(time+1)*100)+100
        pressure_mf = int(np.sin(time+1.8)*100)+100
        pressure_rf = int(np.sin(time+2.5)*100)+100
        pressure_lf = int(np.sin(time+0.4)*100)+100

        msg.pressure = [pressure_ff, pressure_mf, pressure_rf, pressure_lf, pressure_th]

        pub.publish(msg)
        rospy.Rate(10).sleep()
        time = time + 0.1
