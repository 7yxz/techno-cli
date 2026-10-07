from .allanime import AllAnime
from .animepahe import AnimePahe
from .hianime import HiAnime

PROVIDERS = {"animepahe": AnimePahe, "hianime": HiAnime, "allanime": AllAnime}
DEFAULT = "animepahe"
