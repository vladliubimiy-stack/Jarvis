import unittest

from command_parser import extract_wake_command, quick_command


class QuickCommandTests(unittest.TestCase):
    def test_explicit_light_commands(self):
        self.assertEqual(quick_command("Включи свет"), "light_on")
        self.assertEqual(quick_command("Погаси лампу"), "light_off")

    def test_explicit_shutter_commands(self):
        self.assertEqual(quick_command("Открой роллету"), "shutter_open")
        self.assertEqual(quick_command("Закрыть ролету"), "shutter_close")
        self.assertEqual(quick_command("Закрыть роллету"), "shutter_close")
        self.assertEqual(quick_command("Опусти рольставни"), "shutter_close")
        self.assertEqual(quick_command("Останови ворота"), "shutter_stop")

    def test_negated_request_is_never_executed(self):
        self.assertEqual(quick_command("Не надо выключать свет"), "unknown")
        self.assertEqual(quick_command("Не открывай роллету"), "unknown")

    def test_bare_verb_does_not_guess_device(self):
        self.assertEqual(quick_command("Открой"), "unknown")
        self.assertEqual(quick_command("Включи"), "unknown")

    def test_state_statement_is_not_a_command(self):
        self.assertIsNone(quick_command("Свет включён"))

    def test_conflicting_actions_are_rejected(self):
        self.assertEqual(quick_command("Включи и выключи свет"), "unknown")

    def test_non_command_can_use_fallback(self):
        self.assertIsNone(quick_command("Какая сегодня погода?"))
        self.assertIsNone(quick_command("Приопусти рольставню медленно"))

    def test_wake_word_must_be_at_the_start(self):
        self.assertEqual(
            extract_wake_command("Джарвис, включи свет"),
            "включи свет",
        )
        self.assertEqual(
            extract_wake_command("  ДЖАРВИС — закрой ролету"),
            "закрой ролету",
        )
        self.assertIsNone(extract_wake_command("Включи свет"))
        self.assertIsNone(extract_wake_command("Эй, Джарвис, включи свет"))
        self.assertIsNone(extract_wake_command("Я сказал слово Джарвис"))


if __name__ == "__main__":
    unittest.main()
