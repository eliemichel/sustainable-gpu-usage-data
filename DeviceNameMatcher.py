from os.path import dirname, join
import csv
from dataclasses import dataclass
import re
import logging
logger = logging.getLogger(__name__)

from rapidfuzz import process, fuzz
from acora import AcoraBuilder
from fuzzysearch import find_near_matches

#######################################

@dataclass
class DeviceNameMatch:
    # Name of the device found, as listed in the database
    device_name: str

    # Raw normalized match, probably useless (for debug)
    match: str

    # Position of the match within the window
    match_offset: int

    # Matching score (best is 100, although it does not mean "perfect")
    score: int

    # Index of the match in the aggregated database (GPU+CPU), probably useless, prefer relying on device_name
    index: int

    # Window around the match
    window: str

    # Position of the window within the overall text search
    window_offset: int

    # Matched token around which the window was built
    token: str

    # Position of the token within the window
    token_offset: int

#######################################

class DeviceNameMatcher:
    """
    The DeviceNameMatcher tries to locate GPU or CPU names in a long text
    corpus, given a device name database.
    """

    TOKEN_SEPARATORS = " . -/\r\n\t,/()`#\'\""

    @classmethod
    def addCliArguments(cls, parser):
        """
        Add command line arguments specific to this class to an existing
        command line parse created with argparse.ArgumentParser.
        You probably don't want to change the parameters marked as "advanced""
        """
        parser.add_argument(
            '--cpu-database',
            type = str,
            default = join(dirname(__file__), "data", "raw", "devices", "all-cpus.csv"),
            help = "Path to the CPU database.",
        )

        parser.add_argument(
            '--gpu-database',
            type = str,
            default = join(dirname(__file__), "data", "raw", "devices", "all-gpus.csv"),
            help = "Path to the GPU database.",
        )

        parser.add_argument(
            '--min-token-length',
            type = int,
            default = 3,
            help = "(advanced) Discard all tokens smaller than this in the first initial search for token.",
        )

        parser.add_argument(
            '--fuzz-score-cutoff',
            type = int,
            default = 90,
            help = "(advanced) Fuzzy matching score beyond which we reject a match, on a scale from 0 (very permissive) to 100 (very conservative).",
        )

        parser.add_argument(
            '--search-window-radius',
            type = int,
            default = 3,
            help = "(advanced) Number of character added around a potential match before running fuzzy matching.",
        )

    #######################################

    def __init__(self, args):
        """
        Create a matcher from arguments that corresponds to addCliArguments()
        """
        self.testing = False
        self.min_token_length = args.min_token_length
        self.fuzz_score_cutoff = args.fuzz_score_cutoff
        self.search_window_radius = args.search_window_radius

        # Load device names
        self.device_db = {
            #"Intel Core i7": "cpu"",
            #"Intel Xeon E7- 2690v4": "cpu"",
            #"NVIDIA GTX 8000": "gpu"",
        }
        self.loadDeviceNames(args.cpu_database, "cpu")
        self.loadDeviceNames(args.gpu_database, "gpu")
        self.device_names = list(self.device_db.keys())
        logger.info(f"Loaded {len(self.device_names)} device names.")

        # Initial wide match (exact match of tokens across the whole text)
        all_tokens = sum([ self.tokenize(name) for name in self.device_names ], [])
        self.token_offset_lut = self.consolidateTokens(all_tokens)
        logger.info(f"Split into {len(all_tokens)} device name tokens.")
        builder = AcoraBuilder(*self.token_offset_lut.keys(), ignore_case=True)
        self.acora_searcher = builder.build()

        # Detailed match (fuzzy match within a small window)
        self.normalized_device_names = [
            self.normalizeString(s)
            for s in self.device_names
        ]
        self.scorer = fuzz.partial_ratio

    #######################################

    def searchAllDeviceNames(self, text):
        """
        Main entry point, search all device names in a long text
        """
        cursor = 0
        all_matches = []
        for kw, pos in self.acora_searcher.finditer(text):
            # Avoid overlap
            if pos < cursor:
                continue

            # Reject non-token match
            prev_char = text[pos - 1] if pos > 0 else self.TOKEN_SEPARATORS[0]
            next_char = text[pos + len(kw)] if pos + len(kw) < len(text) else self.TOKEN_SEPARATORS[0]
            if prev_char not in self.TOKEN_SEPARATORS or next_char not in self.TOKEN_SEPARATORS:
                continue

            # Establish fuzzy search window
            worst_offset_begin, worst_offset_end = self.token_offset_lut[kw]
            begin_window = max(0, pos - worst_offset_begin - self.search_window_radius)
            end_window = pos + len(kw) + worst_offset_end + self.search_window_radius
            window = text[begin_window:end_window]

            res = self.refineSearch(window)
            if res is None:
                continue

            match, score, index, match_offset = res

            # Check that the match starts within the expected range of start offsets
            # (i.e., that it contains the detected token)
            max_match_offset = self.search_window_radius + worst_offset_begin + 1
            if match_offset > max_match_offset:
                continue

            all_matches.append(DeviceNameMatch(
                device_name = self.device_names[index],
                match = match,
                match_offset = match_offset,
                score = score,
                index = index,
                window = window,
                window_offset = begin_window,
                token = kw,
                token_offset = pos,
            ))

            cursor = end_window - self.search_window_radius

        return all_matches

    #######################################

    def loadDeviceNames(self, db_path, device_type):
        """
        Load device names from a DB, setting their type to 'device_type', which
        is expected to be either 'cpu' or 'gpu'
        """
        with open(db_path, newline='', encoding="utf-8") as f:
            csv_reader = csv.reader(f, delimiter=';', quotechar='"')
            for i, row in enumerate(csv_reader):
                if i == 0:
                    # Header
                    name_col_idx = row.index("Product Name") if "Product Name" in row else row.index("Name")
                    vendor_col_idx = row.index("Vendor")
                else:
                    name = row[name_col_idx]
                    vendor = row[vendor_col_idx]
                    full_name = f"{vendor} {name}"
                    self.device_db[full_name] = device_type

    def tokenize(self, name):
        """
        return tokens and their offset within the original name, from the
        beginning and from the end
        """
        tokens = [ (name, 0, 0) ]
        for sep in self.TOKEN_SEPARATORS:
            next_tokens = []
            for tok, offset_begin, offset_end in tokens:
                local_offset_begin = 0
                for new_tok in tok.split(sep):
                    if len(new_tok) >= self.min_token_length:
                        new_offset_begin = offset_begin + local_offset_begin
                        new_offset_end = offset_end + (len(tok) - local_offset_begin - len(new_tok))
                        next_tokens.append((new_tok, new_offset_begin, new_offset_end))
                    local_offset_begin += len(new_tok) + 1
            tokens = next_tokens
        return tokens

    def consolidateTokens(self, all_tokens):
        """Create a single LUT from token to worst offset"""
        lut = {}
        for token, offset_begin, offset_end in all_tokens:
            prev_offset_begin, prev_offset_end = lut.get(token, (0, 0))
            offset_begin = max(offset_begin, prev_offset_begin)
            offset_end = max(offset_end, prev_offset_end)
            lut[token] = (offset_begin, offset_end)
        return lut

    #######################################

    def normalizeString(self, string):
        """Normalize string to fuzzy match"""
        # Replace any sequence of whitespace chracters by a simple space
        string = re.sub(r"\s+", " ", string.lower())

        # Remove unknown characters
        string = re.sub(r"[^a-zA-Z_0-9 ]", "", string.lower())

        # Add spaces around to foster matching full words
        string = " " + string + " "

        return string

    #######################################

    def normalizeAnMapString(self, string):
        """Same as normalizeString, but creates a map from raw to normalized string (slower)"""
        source_string = string
        mapping = list(range(len(string)))

        string = string.lower()

        # Replace any sequence of whitespace chracters by a simple space
        ctx = { 'offset': 0 }
        def cb(m):
            begin, end = m.span()
            begin += 1
            del mapping[begin-ctx['offset']:end-ctx['offset']]
            ctx['offset'] += end - begin
            return " "
        string = re.sub(r"\s+", cb, string)

        # Remove unknown characters
        ctx = { 'offset': 0 }
        def cb(m):
            begin, end = m.span()
            del mapping[begin-ctx['offset']:end-ctx['offset']]
            ctx['offset'] += end - begin
            return ""
        string = re.sub(r"[^a-zA-Z_0-9 ]", cb, string)

        # Add spaces around to foster matching full words
        string = " " + string + " "
        mapping = [-1] + mapping + [-1]

        return string, mapping

    def test_normalizeAnMapString(self, string):
        source_string = string
        normalized_string, mapping = self.normalizeAnMapString(string)

        whitespace_re = re.compile(r"^\S$")

        for i in range(len(normalized_string)):
            j = mapping[i]
            if j == -1:
                continue
            x = normalized_string[i]
            y = source_string[j]
            if whitespace_re.match(x) == whitespace_re.match(y):
                continue
            if y.lower() != x:
                logger.error(f"Normalized character '{x}' (at index {i}) does not correspond to original character '{y}' (at index {j})")
                logger.info(f"^ With {source_string=} and {normalized_string=}")
                logger.info(f"^ With {mapping=}")
                assert(False)

    #######################################

    def refineSearch(self, text_window):
        """
        Fuzzy search of device name, in a text window expected to be small enough
        """
        res = process.extractOne(
            self.normalizeString(text_window),
            self.normalized_device_names,
            scorer = self.scorer,
            score_cutoff = self.fuzz_score_cutoff
        )

        if res is None:
            return None

        match, score, index = res

        # Estimate offset at which the match starts (because fuzz' process does not provide it)
        if self.testing:
            self.test_normalizeAnMapString(text_window)
        normalized_text, mapping = self.normalizeAnMapString(text_window)
        fs_match = find_near_matches(match, normalized_text, max_l_dist=10)
        if fs_match:
            offset_in_normalized = fs_match[0].start
            # Convert index within normalized text into index within the original text
            offset_in_original = mapping[offset_in_normalized]
            if offset_in_original == -1 and offset_in_normalized < len(mapping) - 1:
                offset_in_original = mapping[offset_in_normalized + 1]
            elif offset_in_original == -1 and offset_in_normalized > 0:
                offset_in_original = mapping[offset_in_normalized - 1]
        else:
            offset_in_normalized = -999
            offset_in_original = -999

        return match, score, index, offset_in_original
