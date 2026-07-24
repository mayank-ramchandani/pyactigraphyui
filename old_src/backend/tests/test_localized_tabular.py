import sys
import tempfile
import types
import unittest
from pathlib import Path

# Keep this regression file runnable without the optional native pyActigraphy stack.
try:
    import pyActigraphy  # noqa: F401
except Exception:
    pyactigraphy_module = types.ModuleType("pyActigraphy")
    pyactigraphy_io_module = types.ModuleType("pyActigraphy.io")

    class _TestBaseRaw:
        pass

    pyactigraphy_io_module.BaseRaw = _TestBaseRaw
    pyactigraphy_module.io = pyactigraphy_io_module
    sys.modules["pyActigraphy"] = pyactigraphy_module
    sys.modules["pyActigraphy.io"] = pyactigraphy_io_module

from backend.io_helpers import (  # noqa: E402
    build_baseraw_from_dataframe,
    infer_reader_type,
    load_auto_tabular,
    load_native_file,
    read_tabular_file,
)


class LocalizedTabularTests(unittest.TestCase):
    def _write(self, directory, name, text, encoding="utf-8"):
        path = Path(directory) / name
        path.write_bytes(text.encode(encoding))
        return path

    def test_french_windows_1252_rpx_is_decoded_and_loaded(self):
        content = "\n".join(
            [
                '"Fichier d\'exportation Actiware (Version 05.00)"',
                '"Nom de fichier\u00a0:","exemple"',
                '"Ligne","Secondes","Date","Heure","Activité","Marqueur","Lumière blanche"',
                '"1","0","04/02/2015","11:45:00","0","0","12,5"',
                '"2","60","04/02/2015","11:46:00","11","0","20,0"',
                '"3","120","04/02/2015","11:47:00","4","0","18,0"',
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, "fr_cp1252.csv", content, "cp1252")
            self.assertEqual(infer_reader_type(str(path)), "rpx")
            mapped, mapping = load_auto_tabular(str(path))
            raw = build_baseraw_from_dataframe(mapped, name=path.name)

        self.assertEqual(mapping["activity_col"], "Activité")
        self.assertEqual(mapping["light_col"], "Lumière blanche")
        self.assertEqual(mapped.attrs["source_encoding"], "cp1252")
        self.assertEqual(raw.light.get_channel_list(), ["LIGHT"])
        self.assertEqual(float(raw.data.iloc[1]), 11.0)
        self.assertAlmostEqual(float(raw.light.get_channel("LIGHT").iloc[0]), 12.5)

    def test_german_rpx_preserves_rgb_channels_and_no_light_is_allowed(self):
        with_light = "\n".join(
            [
                '"Actiware-Exportdatei (Version 05.00 )"',
                '"Zeile","Datum","Zeit","Aktivität","Markierung","Weißes Licht","Rotes Licht","Grünes Licht","Blaues Licht"',
                '"1","04.02.2015","11:45:00","2","0","10,0","1,0","2,0","3,0"',
                '"2","04.02.2015","11:46:00","3","0","11,0","1,5","2,5","3,5"',
            ]
        )
        no_light = "\n".join(
            [
                '"Actiware-Exportdatei (Version 05.00 )"',
                '"Zeile","Datum","Zeit","Status „Nicht am Handgelenk“","Aktivität"',
                '"1","04.02.2015","11:45:00","0","2"',
                '"2","04.02.2015","11:46:00","0","3"',
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            light_path = self._write(directory, "with_light.csv", with_light)
            no_light_path = self._write(directory, "no_light.csv", no_light)
            light_df, _ = load_auto_tabular(str(light_path))
            no_light_df, _ = load_auto_tabular(str(no_light_path))
            light_raw = build_baseraw_from_dataframe(light_df)
            no_light_raw = build_baseraw_from_dataframe(no_light_df)

        self.assertEqual(
            light_raw.light.get_channel_list(),
            ["LIGHT", "RED LIGHT", "GREEN LIGHT", "BLUE LIGHT"],
        )
        self.assertEqual(no_light_raw.light.get_channel_list(), [])

    def test_localized_rpx_csv_bypasses_pyactigraphy_data_offset_reader(self):
        content = "\n".join(
            [
                '"Fichier d\'exportation Actiware (Version 05.00)"',
                '"Ligne","Date","Heure","Activité"',
                '"1","04/02/2015","11:45:00","1"',
                '"2","04/02/2015","11:46:00","2"',
            ]
        )
        import pyActigraphy

        original = getattr(pyActigraphy.io, "read_raw_rpx", None)
        pyActigraphy.io.read_raw_rpx = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("native RPX reader should not be called for localized CSV")
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = self._write(directory, "fr.csv", content)
                raw = load_native_file(str(path), "rpx")
            self.assertEqual(len(raw.data), 2)
        finally:
            if original is None:
                delattr(pyActigraphy.io, "read_raw_rpx")
            else:
                pyActigraphy.io.read_raw_rpx = original

    def test_generic_csv_auto_mapping_is_supported(self):
        content = "timestamp,activity,light\n2026-01-01 00:00:00,1,10\n2026-01-01 00:01:00,2,20\n"
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, "generic.csv", content)
            self.assertEqual(infer_reader_type(str(path)), "tabular")
            parsed = read_tabular_file(str(path))
            mapped, mapping = load_auto_tabular(str(path))

        self.assertEqual(list(parsed.columns), ["timestamp", "activity", "light"])
        self.assertEqual(mapping["timestamp_col"], "timestamp")
        self.assertEqual(mapping["activity_col"], "activity")
        self.assertEqual(mapping["light_col"], "light")
        self.assertEqual(len(mapped), 2)

    def test_nhanes_paxhr_returns_specific_preparation_guidance(self):
        content = (
            "SEQN,PAXDAYH,PAXDAYWH,PAXSSNHP,PAXTMH,PAXMTSH,PAXLXSH\n"
            "1001,1,2,0,60,120.5,300\n"
            "1001,1,2,288000,60,95.0,200\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, "PAXHR_H.csv", content)
            with self.assertRaisesRegex(ValueError, "NHANES PAXHR_H cohort-level hour-summary"):
                load_auto_tabular(str(path))


if __name__ == "__main__":
    unittest.main()
