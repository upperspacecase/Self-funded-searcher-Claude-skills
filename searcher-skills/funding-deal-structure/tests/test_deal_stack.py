import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from deal_stack import structure, annual_payment, max_spread, max_price_at_dscr

def test_amortisation():
    # $100,000 at 12% over 1 year -> monthly 8,884.88 -> annual 106,618.55
    assert abs(annual_payment(100_000, 12, 1) - 106_618.55) < 1
    assert annual_payment(0, 10, 10) == 0

def test_spreads():
    assert max_spread(50_000) == 6.5 and max_spread(250_000) == 6.0 and max_spread(350_000) == 4.5 and max_spread(350_001) == 3.0

def test_injection_math():
    r = structure(price=900_000, sde=310_000, cash=120_000, salary=100_000, prime=6.75, working_capital=50_000, closing_costs=25_000,
                  seller_note=100_000, seller_standby='full', seller_rate=6, seller_years=10)
    assert r['total_project_cost'] == 975_000
    assert r['required_injection_10pct'] == 97_500
    assert r['limited_source_credit'] == 48_750            # capped at half the injection
    assert r['buyer_cash_in'] == 48_750
    assert r['bank_loan'] == 975_000 - 48_750 - 100_000
    assert r['bank_spread_pct'] == 3.0 and abs(r['bank_rate_pct'] - 9.75) < 1e-9
    assert r['seller_debt_service_counted'] == 0 and 'seller_note_over_credit' in r['flags']

def test_partial_standby_counts_in_dscr():
    r = structure(price=900_000, sde=310_000, cash=120_000, salary=100_000, prime=6.75, seller_note=180_000, seller_standby='partial',
                  seller_rate=6, seller_years=7, seller_io_years=2)
    assert r['limited_source_credit'] == 0 and r['buyer_cash_in'] == 90_000
    assert r['seller_debt_service_counted'] > 0 and 'seller_note_in_dscr' in r['flags']
    assert r['seller_debt_service_actual_yr1'] == 180_000 * 0.06

def test_shortfall_flag():
    r = structure(price=900_000, sde=310_000, cash=40_000, salary=100_000, prime=6.75)
    assert 'equity_shortfall' in r['flags']

def test_max_price_monotone():
    kw = dict(price=900_000, sde=310_000, cash=500_000, salary=100_000, prime=6.75, seller_note=0, seller_standby='none', seller_rate=6, seller_years=0)
    p = max_price_at_dscr(kw, 1.25)
    kw2 = dict(kw); kw2['price'] = p
    assert abs(structure(**kw2)['dscr'] - 1.25) < 0.01

if __name__ == '__main__':
    for fn in (test_amortisation, test_spreads, test_injection_math, test_partial_standby_counts_in_dscr, test_shortfall_flag, test_max_price_monotone):
        fn(); print('PASS', fn.__name__)
