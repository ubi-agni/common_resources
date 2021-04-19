#!/usr/bin/env python

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

import rospy
import speech_recognition as sr
from difflib import get_close_matches
from std_msgs.msg import String


class SpeechControl(object):
    def __init__(self):
        self.microphone = sr.Microphone()
        prefer_microphone = rospy.get_param('~prefer_microphone')
        if prefer_microphone:
            for i, microphone_name in enumerate(sr.Microphone.list_microphone_names()):
                if prefer_microphone in microphone_name:
                    self.microphone = sr.Microphone(device_index=i)
                    rospy.loginfo("Using preferred microphone: {}".format(microphone_name))
                    break
        self.trigger_word = rospy.get_param('~trigger_word', 'shadow')
        self.recognizer = sr.Recognizer()
        self._set_param_if_provided(self.recognizer, 'non_speaking_duration')
        self._set_param_if_provided(self.recognizer, 'pause_threshold')
        self.command_words = rospy.get_param('~command_words', [])
        topic = rospy.get_param('~topic', 'sr_speech_control')
        self.command_publisher = rospy.Publisher(topic, String, queue_size=1)
        self._stop_listening = self.recognizer.listen_in_background(self.microphone, self._recognizer_callback)

    def _set_param_if_provided(self, object_to_set, param_name):
        if rospy.has_param('~' + param_name):
            setattr(object_to_set, param_name, rospy.get_param('~' + param_name))

    def _recognizer_callback(self, recognizer, audio):
        try:
            result = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return
        except sr.RequestError as e:
            rospy.logwarn("Could not request results from Google Speech Recognition service: {}".format(e))
            return

        result = [str(x).lower() for x in result.split(' ')]
        if len(result) > 1:
            if self._filter_word(result[0], [self.trigger_word]) == self.trigger_word:
                self.command_publisher.publish(' '.join([self._filter_word(x, self.command_words) for x in result[1:]]))

    def _filter_word(self, word, dictionary, offset=0.5):
        result = get_close_matches(word, dictionary, 1, offset)
        if not result:
            return word
        return result[0]

if __name__ == "__main__":
    rospy.init_node('sr_speech_control', anonymous=True)

    sc = SpeechControl()
    rospy.loginfo("Started speech control. Trigger word: {}, command words: {}".format(
        sc.trigger_word, sc.command_words))
    rospy.spin()
    sc._stop_listening(wait_for_stop=False)