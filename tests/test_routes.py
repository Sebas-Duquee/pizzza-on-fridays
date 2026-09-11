from app.models.market_data import Quote
from app.models.watchlists import WATCHLISTS


def _fake_quote(ticker):
    return Quote(
        symbol=ticker,
        name=ticker,
        price=100.0,
        previous_close=95.0,
        change=5.0,
        change_percent=5.263,
        currency="USD",
    )


def test_index_redirects_to_default_watchlist(client):
    response = client.get("/")
    assert response.status_code == 302
    assert f"/w/{WATCHLISTS[0].slug}" in response.headers["Location"]


def test_unknown_watchlist_is_404(client):
    assert client.get("/w/no-existe").status_code == 404


def test_show_watchlist_renders_first_symbol(client):
    watchlist = WATCHLISTS[0]
    response = client.get(f"/w/{watchlist.slug}")
    assert response.status_code == 200
    assert watchlist.symbols[0].ticker.encode() in response.data


def test_api_quote(client, monkeypatch):
    monkeypatch.setattr("app.controllers.api.market_data.get_quote", _fake_quote)
    response = client.get("/api/quote/AAPL")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["symbol"] == "AAPL"
    assert payload["is_up"] is True


def test_api_candles_rejects_bad_params(client):
    response = client.get("/api/candles/AAPL?range=bogus&interval=1d")
    assert response.status_code == 400
