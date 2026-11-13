import unittest
import numpy as np
import pandas as pd
from validation.compare_outputs import compare_frames
from validation.compare_three import compare_three


class AgreementTests(unittest.TestCase):
    def setUp(self):
        self.actilab=pd.DataFrame({'source_file':['A','B','C','D'],
            'ra':[.1,.2,.3,.4],'valid_day':[True,False,True,False]})
        self.ggir=pd.DataFrame({'source_file':['A','B','C','D'],
            'RA':[.1,.25,.25,.4],'valid_day':[True,False,False,False]})
        self.py=pd.DataFrame({'source_file':['A','B','C','D'],
            'RA':[.1,.2,.3,.39],'valid_day':[True,False,True,False]})

    def test_numeric_statistics_and_kappa(self):
        report,joined=compare_frames(self.actilab,self.ggir,['source_file'],[('ra','RA')],
              categorical_pairs=[('valid_day','valid_day')],positive='True')
        a=report.loc[report.kind=='continuous'].iloc[0]
        c=report.loc[report.kind=='categorical'].iloc[0]
        self.assertEqual(int(a.numeric_pairs),4)
        self.assertAlmostEqual(a.bias,0)
        self.assertAlmostEqual(a.mae,.025)
        self.assertLess(a.lin_ccc,1)
        self.assertEqual(c.category_pairs,4)
        self.assertAlmostEqual(c.cohen_kappa,.5)
        self.assertAlmostEqual(c.percent_agreement,75)
        self.assertEqual(c.TP,1)
        self.assertEqual(len(joined),4)

    def test_three_way_and_partial_intersection(self):
        pp,overall,triples=compare_three([self.actilab,self.ggir,self.py],['source_file'],{
            'continuous':{'RA':['ra','RA','RA']},
            'categorical':{'valid':['valid_day','valid_day','valid_day']}})
        self.assertEqual(len(pp),6)
        self.assertEqual(len(triples),4)
        self.assertAlmostEqual(overall.loc[overall.metric=='valid','three_way_percent_agreement'].iloc[0],75)
        self.assertEqual(int(overall.loc[overall.metric=='RA','n_triplets'].iloc[0]),4)

    def test_duplicate_keys_fail(self):
        left=pd.concat([self.actilab,self.actilab.iloc[:1]],ignore_index=True)
        with self.assertRaises(ValueError):
            compare_frames(left,self.ggir,['source_file'],[('ra','RA')])

if __name__=='__main__':unittest.main()
