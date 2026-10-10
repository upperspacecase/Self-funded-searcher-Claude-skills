"""Build small synthetic inputs that mimic the real file layouts, for offline tests."""
import os, pandas as pd
d = os.path.join(os.path.dirname(__file__), 'fixtures', 'data'); os.makedirs(d, exist_ok=True)
# registry (post-parse layout from fetch_sunbiz.py)
reg = pd.DataFrame([
 dict(cor_number='123456', cor_name='ADVENT AIR CONDITIONING, INC.', status='A', filing_type='DOMP', addr1='1 MAIN', city='TAMPA', state='FL', zip='33602', file_date_iso='1984-03-15', fei='59-1234567', last_txn_iso='2026-04-01', report_year1='2026', state_country='FL', ra_name='X', off1_title='PRES', off1_name='SMITH, JOHN A', off2_title='VP', off2_name='SMITH, MARY B', off3_title='', off3_name='', off4_title='', off4_name='', off5_title='', off5_name='', off6_title='', off6_name=''),
 dict(cor_number='223456', cor_name='THE LEE THOMPSON CO', status='A', filing_type='DOMP', addr1='2 MAIN', city='ORLANDO', state='FL', zip='32801', file_date_iso='1961-06-01', fei='591111111', last_txn_iso='2026-04-01', report_year1='2026', state_country='FL', ra_name='X', off1_title='PRES', off1_name='THOMPSON, LEE', off2_title='SECR', off2_name='GARCIA, ANA', off3_title='', off3_name='', off4_title='', off4_name='', off5_title='', off5_name='', off6_title='', off6_name=''),
 dict(cor_number='323456', cor_name='NEWCO PLUMBING LLC', status='A', filing_type='FLAL', addr1='3 MAIN', city='TAMPA', state='FL', zip='33602', file_date_iso='2019-01-01', fei='', last_txn_iso='2026-04-01', report_year1='2026', state_country='FL', ra_name='X', off1_title='MGR', off1_name='LOPEZ, R', off2_title='', off2_name='', off3_title='', off3_name='', off4_title='', off4_name='', off5_title='', off5_name='', off6_title='', off6_name=''),
 dict(cor_number='423456', cor_name='CARY SERVICES INC', status='A', filing_type='DOMP', addr1='4 MAIN', city='MIAMI', state='FL', zip='33131', file_date_iso='1995-02-02', fei='', last_txn_iso='2026-04-01', report_year1='2026', state_country='FL', ra_name='X', off1_title='PRES', off1_name='CARY, TOM', off2_title='', off2_name='', off3_title='', off3_name='', off4_title='', off4_name='', off5_title='', off5_name='', off6_title='', off6_name=''),
])
reg.to_csv(os.path.join(d, 'sunbiz_active.csv'), index=False)
ppp = pd.DataFrame([
 dict(loan_number='1', date_approved='04/15/2020', name='Advent Air Conditioning Inc', address='1 Main St', city='Tampa', state='FL', zip='33602-1234', naics='238220', amount='480000', forgiven='480000', jobs='41', business_type='Corporation', source='ppp', source_file='x'),
 dict(loan_number='2', date_approved='04/20/2020', name='Lee Thompson Co Inc', address='2 Main St', city='Orlando', state='FL', zip='32801', naics='238220', amount='900000', forgiven='600000', jobs='70', business_type='Corporation', source='ppp', source_file='x'),
 dict(loan_number='3', date_approved='05/01/2020', name='Newco Plumbing LLC', address='3 Main St', city='Tampa', state='FL', zip='33602', naics='238220', amount='160000', forgiven='160000', jobs='12', business_type='LLC', source='ppp', source_file='x'),
 dict(loan_number='4', date_approved='05/01/2020', name='Ghost Mechanical Corp', address='9 Nowhere', city='Jacksonville', state='FL', zip='32202', naics='238220', amount='200000', forgiven='200000', jobs='15', business_type='Corporation', source='ppp', source_file='x'),
])
ppp.to_csv(os.path.join(d, 'sba_ppp_FL_238220.csv'), index=False)
sev = pd.DataFrame([
 dict(name='CARY SERVICES, INC.', address='4 Main', city='MIAMI', state='FL', zip='33131', naics='238220', amount='350000', date_approved='2015-08-01', jobs='9', business_age='Existing or more than 2 years old', loan_status='PIF', term_months='120', source='7a', source_file='x'),
])
sev.to_csv(os.path.join(d, 'sba_7a_FL_238220.csv'), index=False)
f5500 = pd.DataFrame([
 dict(name='ADVENT AIR CONDITIONING INC', ein='591234567', city='TAMPA', state='FL', zip='33602', participants_boy=44, active_participants=39, plan_year_begin='2024-01-01', business_code='238220', plan_name='ADVENT 401K', form='sf', form_year=2024, ein_key='591234567'),
 dict(name='LEE THOMPSON COMPANY', ein='59-9999999', city='ORLANDO', state='FL', zip='32801', participants_boy=80, active_participants=72, plan_year_begin='2024-01-01', business_code='238220', plan_name='LT 401K', form='sf', form_year=2024, ein_key='599999999'),
])
f5500.to_csv(os.path.join(d, 'f5500_FL.csv'), index=False)
print('fixtures written to', d)
