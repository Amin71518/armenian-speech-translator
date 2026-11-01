import sys
from types import SimpleNamespace

import pytest

from armenian_speech import launcher


def arguments(**updates):
    return SimpleNamespace(**dict({'microphone_device': None, 'device': None,
                                  'microphone_rate': None, 'microphone_channels': 1}, **updates))


class Audio:
    mic_id = 9
    rate = 48000

    def query_hostapis(self):
        return [{'name': 'MME', 'default_input_device': 1},
                {'name': 'Windows WASAPI', 'default_input_device': self.mic_id}]

    def query_devices(self, device, kind):
        assert kind == 'input'
        return {'name': 'Test microphone', 'default_samplerate': self.rate}

    def check_input_settings(self, **settings):
        self.checked = settings


class Manager:
    loop_id = 10
    closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def get_default_wasapi_loopback(self):
        return {'index': self.loop_id}

    def get_device_info_by_index(self, device):
        return {'name': 'Test loopback', 'index': device,
                'isLoopbackDevice': True, 'maxInputChannels': 2}


def test_current_defaults_are_resolved_each_time_including_native_headset_rate():
    audio, manager = Audio(), Manager()
    assert launcher.choose_devices(arguments(), audio, manager)[:2] == (9, 48000)
    audio.mic_id, audio.rate, manager.loop_id = 15, 16000, 16
    result = launcher.choose_devices(arguments(), audio, manager)
    assert (result[0], result[1], result[3]) == (15, 16000, 16)
    assert audio.checked['samplerate'] == 16000 and audio.checked['channels'] == 1


def test_explicit_devices_do_not_depend_on_windows_defaults():
    audio, manager = Audio(), Manager()
    audio.query_hostapis = lambda: pytest.fail('Unexpected default microphone lookup')
    manager.get_default_wasapi_loopback = lambda: pytest.fail('Unexpected default loopback lookup')
    result = launcher.choose_devices(arguments(microphone_device=3, device=8,
                                               microphone_rate=44100), audio, manager)
    assert (result[0], result[1], result[3]) == (3, 44100, 8)


def test_launcher_closes_discovery_manager_and_forwards_selected_configuration(monkeypatch):
    manager = Manager()
    monkeypatch.setitem(sys.modules, 'pyaudiowpatch', SimpleNamespace(PyAudio=lambda: manager))
    monkeypatch.setattr(launcher.combined, 'sd', Audio())
    calls = []

    def combined(argv):
        assert manager.closed
        calls.append(argv)
        return 130

    monkeypatch.setattr(launcher.combined, 'main', combined)
    assert launcher.main(['--duration', '3', '--speaker-diagnostics']) == 130
    argv, = calls
    assert argv[:3] == ['--duration', '3', '--speaker-diagnostics']
    assert argv[-2:] == ['--diarize', '--experimental-speaker-matching']
    assert argv[argv.index('--microphone-rate') + 1] == '48000'


def test_no_default_microphone_fails_without_fallback_or_inference(monkeypatch, capsys):
    audio, manager = Audio(), Manager()
    audio.mic_id = -1
    audio.PortAudioError = RuntimeError
    monkeypatch.setattr(launcher.combined, 'sd', audio)
    monkeypatch.setitem(sys.modules, 'pyaudiowpatch', SimpleNamespace(PyAudio=lambda: manager))
    monkeypatch.setattr(launcher.combined, 'main', lambda _: pytest.fail('Inference started'))
    assert launcher.main([]) == 1
    assert manager.closed and 'No default WASAPI microphone' in capsys.readouterr().err


def test_help_and_listing_never_resolve_or_open_capture(monkeypatch):
    monkeypatch.setattr(launcher, 'choose_devices', lambda *a: pytest.fail('Discovery ran'))
    monkeypatch.setattr(launcher.combined, 'main', lambda argv: argv)
    assert launcher.main(['--list-devices']) == ['--list-devices']
    with pytest.raises(SystemExit, match='0'):
        launcher.main(['--help'])
