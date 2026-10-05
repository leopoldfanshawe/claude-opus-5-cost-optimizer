import unittest
from decimal import Decimal
from estimate_cost import estimate
class T(unittest.TestCase):
 def test_breakdown(self):
  x=estimate({'input_tokens':1000000,'output_tokens':1000000,'cached_input_tokens':1000000,'cache_write_tokens':1000000})
  self.assertEqual(x['total'],'29.200000'); self.assertEqual(x['model'],'claude-opus-5-5')
 def test_missing_is_zero(self): self.assertEqual(estimate({})['total'],'0.000000')
if __name__=='__main__': unittest.main()
