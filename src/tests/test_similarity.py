from tests import PySparkTestCase

import pyspark.sql.functions as f
from pyspark.sql.types import *

from similarity import Similarity

import pandas as pd


class TestSimilarity(PySparkTestCase):

    def test__add_rank_column(self):

        pd_df_similarities_long = pd.read_csv('tests/fixtures/similarity/similarities_long.csv')

        df_simple_table = self.spark.read.csv('tests/fixtures/similarity/simple_table_id.csv', header=True)
        columns_to_convert = [col for col in df_simple_table.columns if 'id' not in col]
        for col in columns_to_convert:
            df_simple_table = df_simple_table.withColumn(col, f.col(col).cast(IntegerType()))
        similarity_cosine = Similarity(df_features=df_simple_table, index_column='id', similarity_type='cosine')

        pd_df_with_rank_cosine = similarity_cosine._add_rank_column(pd_df_similarities_long)
        check_id_1_1_cosine = pd_df_with_rank_cosine.loc[(pd_df_with_rank_cosine['id_1'] == 1)
                                                         & (pd_df_with_rank_cosine['id_2'] == 1)]['rank'].values[0]
        self.assertEqual(check_id_1_1_cosine, 1)

        check_id_1_3_cosine = pd_df_with_rank_cosine.loc[(pd_df_with_rank_cosine['id_1'] == 1)
                                                         & (pd_df_with_rank_cosine['id_2'] == 3)]['rank'].values[0]
        self.assertEqual(check_id_1_3_cosine, 3)

        check_id_3_3_cosine = pd_df_with_rank_cosine.loc[(pd_df_with_rank_cosine['id_1'] == 3)
                                                         & (pd_df_with_rank_cosine['id_2'] == 3)]['rank'].values[0]
        self.assertEqual(check_id_3_3_cosine, 1)

        similarity_euclidean = Similarity(df_features=df_simple_table, index_column='id', similarity_type='euclidean')

        pd_df_with_rank_euclidean = similarity_euclidean._add_rank_column(pd_df_similarities_long)

        check_id_3_3_euclidean = pd_df_with_rank_euclidean.loc[(pd_df_with_rank_euclidean['id_1'] == 3)
                                                               & (pd_df_with_rank_euclidean['id_2'] == 3)]['rank'].values[0]
        self.assertEqual(check_id_3_3_euclidean, 3)

        pd_df_similarities_long_dupes = pd.read_csv('tests/fixtures/similarity/similarities_long_dupes.csv')

        cnt = 0
        for i in range(5):
            similarity_cosine_dupes = Similarity(df_features=df_simple_table, index_column='id', similarity_type='cosine')
            pd_df_with_rank_cosine_dupes = similarity_cosine_dupes._add_rank_column(pd_df_similarities_long_dupes)

            check_id_1_5_dupes = pd_df_with_rank_cosine_dupes.loc[(pd_df_with_rank_cosine_dupes['id_1'] == 1)
                                                                  & (pd_df_with_rank_cosine_dupes['id_2'] == 5)]['rank'].values[0]

            cnt += 1 if check_id_1_5_dupes == 1 else 0

        self.assertTrue(cnt < 5)

    def test__check_is_spark_data_frame(self):

        df_simple_table = self.spark.read.csv('tests/fixtures/similarity/simple_table.csv', header=True)
        pd_df_simple_table = pd.read_csv('tests/fixtures/similarity/simple_table.csv')

        columns_to_convert = [col for col in df_simple_table.columns if 'id' not in col]
        for col in columns_to_convert:
            df_simple_table = df_simple_table.withColumn(col, f.col(col).cast(IntegerType()))

        Similarity(df_features=df_simple_table)

        with self.assertRaises(AssertionError):
            Similarity(df_features=pd_df_simple_table)

    def test__check_nulls_in_feature_columns(self):

        df_nulls_features = self.spark.read.csv('tests/fixtures/similarity/nulls_features.csv', header=True)
        df_no_nulls_features = self.spark.read.csv('tests/fixtures/similarity/no_nulls_features.csv', header=True)

        columns_to_convert_nulls = [col for col in df_nulls_features.columns if 'id' not in col]
        for col in columns_to_convert_nulls:
            df_nulls_features = df_nulls_features.withColumn(col, f.col(col).cast(IntegerType()))

        columns_to_convert_no_nulls = [col for col in df_no_nulls_features.columns if 'id' not in col]
        for col in columns_to_convert_no_nulls:
            df_no_nulls_features = df_no_nulls_features.withColumn(col, f.col(col).cast(IntegerType()))

        Similarity(df_features=df_no_nulls_features)

        with self.assertRaises(AssertionError):
            Similarity(df_features=df_nulls_features)

    def test__check_is_numerical_data(self):

        df_numerical = self.spark.read.csv('tests/fixtures/similarity/numerical_data.csv', header=True)

        columns_to_convert = [col for col in df_numerical.columns if 'id' not in col]
        df_numerical_int = df_numerical
        df_numerical_float = df_numerical

        for col in columns_to_convert:
            df_numerical_int = df_numerical_int.withColumn(col, f.col(col).cast(IntegerType()))
            df_numerical_float = df_numerical_float.withColumn(col, f.col(col).cast(DoubleType()))

        Similarity(df_features=df_numerical_int)
        Similarity(df_features=df_numerical_float)

        with self.assertRaises(AssertionError):
            Similarity(df_features=df_numerical)

    def test_generate(self):

        df_features = self.spark.read.csv('tests/fixtures/similarity/features.csv', header=True)

        columns_to_convert = [col for col in df_features.columns if 'id' not in col]
        df_features_int = df_features
        for col in columns_to_convert:
            df_features_int = df_features_int.withColumn(col, f.col(col).cast(IntegerType()))

        similarity_cos = Similarity(df_features=df_features_int, similarity_type='cosine')

        pd_df_similarity_cos, _ = similarity_cos.generate()

        self.assertEqual(pd_df_similarity_cos.shape[0], df_features.count())
        self.assertEqual(pd_df_similarity_cos.shape[1], df_features.count())

        similarity_euc = Similarity(df_features=df_features_int, similarity_type='euclidean')

        pd_df_similarity_euc, _ = similarity_euc.generate()

        self.assertEqual(pd_df_similarity_euc.shape[0], df_features.count())
        self.assertEqual(pd_df_similarity_euc.shape[1], df_features.count())

        similarity_fail = Similarity(df_features=df_features_int, similarity_type='test')
        with self.assertRaises(ValueError):
            similarity_fail.generate()

    def test__convert_to_long_format(self):

        pd_df_similarities_wide = pd.read_csv('tests/fixtures/similarity/similarities_wide.csv', index_col=0)

        df_simple_table = self.spark.read.csv('tests/fixtures/similarity/simple_table.csv', header=True)
        columns_to_convert = [col for col in df_simple_table.columns if 'id' not in col]
        for col in columns_to_convert:
            df_simple_table = df_simple_table.withColumn(col, f.col(col).cast(IntegerType()))
        similarity = Similarity(df_features=df_simple_table)

        pd_df_similarities_long = similarity._convert_to_long_format(pd_df_similarities_wide)

        self.assertEqual(pd_df_similarities_long.shape[0],
                         pd_df_similarities_wide.shape[0]*pd_df_similarities_wide.shape[1])

        check_1_3 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 1)
                                                & (pd_df_similarities_long['recipe_id_2'] == '3')]['similarity'].values[0]
        self.assertEqual(check_1_3, 9)

        check_3_1 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 3)
                                                & (pd_df_similarities_long['recipe_id_2'] == '1')]['similarity'].values[0]
        self.assertEqual(check_3_1, 6)

        check_2_3 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 2)
                                                & (pd_df_similarities_long['recipe_id_2'] == '3')]['similarity'].values[0]
        self.assertEqual(check_2_3, 1)

        check_1_2 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 1)
                                                & (pd_df_similarities_long['recipe_id_2'] == '2')]['similarity'].values[0]
        self.assertEqual(check_1_2, 6)

