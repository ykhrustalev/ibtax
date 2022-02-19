import pathlib
import pickle


class PickleCache:
    def __init__(self, path: pathlib.Path):
        self.path = path

    def _path(self, key):
        return self.path / key

    def get(self, key):
        path = self._path(key)
        if path.is_file():
            with path.open("rb") as f:
                return pickle.load(f)

    def set(self, key, value):
        path = self._path(key)
        with path.open("wb") as f:
            pickle.dump(value, f)
