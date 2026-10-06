from .allanime import AllAnime
from .animepahe import AnimePahe
from .aniwatch import AniwatchAPI
from .hianime import HiAnime

PROVIDERS = {"animepahe": AnimePahe, "hianime": HiAnime, "allanime": AllAnime,
             "aniwatch": AniwatchAPI}
DEFAULT = "animepahe"
