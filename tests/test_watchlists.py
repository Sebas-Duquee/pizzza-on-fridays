from app.models.watchlists import WATCHLISTS, default_watchlist, get_symbol, get_watchlist


def test_default_watchlist_is_first():
    assert default_watchlist() is WATCHLISTS[0]


def test_get_watchlist_found_and_missing():
    assert get_watchlist(WATCHLISTS[0].slug) is WATCHLISTS[0]
    assert get_watchlist("no-existe") is None


def test_get_symbol_found_and_missing():
    watchlist = WATCHLISTS[0]
    ticker = watchlist.symbols[0].ticker
    assert get_symbol(watchlist, ticker) is watchlist.symbols[0]
    assert get_symbol(watchlist, "NOPE") is None


def test_slugs_are_unique():
    slugs = [w.slug for w in WATCHLISTS]
    assert len(slugs) == len(set(slugs))
