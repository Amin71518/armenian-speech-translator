"""Launch the selected live configuration using current Windows defaults or explicit IDs."""

import sys

from armenian_speech import combined
from armenian_speech.system_audio import select_device


def choose_devices(args, audio, manager):
    mic_id = args.microphone_device
    if mic_id is None:
        wasapi = next((api for api in audio.query_hostapis() if api['name'] == 'Windows WASAPI'),
                      None)
        if wasapi is None or wasapi['default_input_device'] < 0:
            raise ValueError('No default WASAPI microphone. Use --microphone-device INPUT_ID.')
        mic_id = wasapi['default_input_device']
    mic = audio.query_devices(mic_id, 'input')
    rate = args.microphone_rate or int(mic['default_samplerate'])
    audio.check_input_settings(device=mic_id, samplerate=rate,
                               channels=args.microphone_channels, dtype='int16')
    loop_id = args.device
    if loop_id is None:
        loop_id = int(manager.get_default_wasapi_loopback()['index'])
    loop = select_device(manager, loop_id)
    return int(mic_id), rate, mic, int(loop_id), loop


def main(argv=None):
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, 'reconfigure'):
            output.reconfigure(encoding='utf-8')
    argv = list(sys.argv[1:] if argv is None else argv)
    cli = combined.argument_parser()
    cli.description = __doc__
    cli.epilog = ('Starts with --diarize --experimental-speaker-matching. '
                  'Default devices are selected once at startup; override IDs if the call '
                  'uses a different output. Use the combined module for baseline modes.')
    cli.set_defaults(microphone_rate=None)
    args = cli.parse_args(argv)
    if args.list_devices:
        return combined.main(argv)
    try:
        import pyaudiowpatch
        with pyaudiowpatch.PyAudio() as manager:
            mic_id, rate, mic, loop_id, loop = choose_devices(args, combined.sd, manager)
        print(f"Microphone {mic_id}: {mic['name']} | {rate} Hz", flush=True)
        print(f"System loopback {loop_id}: {loop['name']}", flush=True)
        print('Using these devices for this session. The call must play through this output.',
              flush=True)
        return combined.main([*argv, '--microphone-device', str(mic_id),
                              '--microphone-rate', str(rate), '--device', str(loop_id),
                              '--diarize', '--experimental-speaker-matching'])
    except (ImportError, OSError, ValueError, LookupError, combined.sd.PortAudioError) as error:
        print(f'Audio device selection failed: {error}\n'
              'Run main.py --list-devices and select --microphone-device / --device explicitly.',
              file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
