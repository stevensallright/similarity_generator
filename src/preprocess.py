from pyspark.sql import DataFrame
import pyspark.sql.functions as f
from pyspark.sql.types import *
from pyspark.sql import Window


class Preprocess(object):
    """
    Prepare data for similarity calculation.

    """

    def __init__(self, df_labels, columns, index_column='recipe_id'):
        """
        Performs the following assumption checks/manipulations during initialization:
            - checks if "df_labels" is a spark data frame
            - checks "columns" is a list or "all"
            - convert "columns" to list of strings containing all columns from "df_labels"
            - checks nulls in index_column
            - removes duplicates from index_column
            - checks if attribute columns contain nulls

        :param df_labels: spark data frame
        :param columns: list of string, columns to use for similarity calculation
        :param index_column: string, columns to use for similarity calculation
        """

        self.df_labels = df_labels
        self.columns = columns
        self.index_column = index_column

        self._check_is_spark_data_frame()
        self._check_is_list()
        self._convert_column_argument()
        self._check_nulls_in_index_column()
        self._remove_duplicate_indexes()
        self._check_nulls_in_attribute_columns()

    def _convert_column_argument(self):
        """
        Converts column argument to list of columns names in df_labels (without index_column).

        :return:
        """

        if self.columns == 'all':
            self.columns = [col for col in self.df_labels.columns if col != self.index_column]

    def _remove_duplicate_indexes(self):
        """
        Removes duplicate recipes by randomly selecting one if duplicated.

        :return:
        """

        window = Window \
            .partitionBy([self.index_column]) \
            .orderBy(f.rand())

        self.df_labels = self.df_labels\
            .withColumn('rn', f.row_number().over(window))\
            .filter(f.col('rn') == 1)\
            .drop('rn')

    def _check_is_list(self):
        """
        Checks "columns" is a list.

        :return:
        """

        if self.columns is not 'all':
            assert isinstance(self.columns, list), '"columns" has to be a list.'

    def _check_is_spark_data_frame(self):
        """
        Checks if df_labels is a spark data frame.

        :return:
        """

        assert isinstance(self.df_labels, DataFrame), '"df_labels" is not a spark data frame.'

    def _check_nulls_in_index_column(self):
        """
        Checks if column "recipe_id" contains nulls.

        :return:
        """

        null_count = self.df_labels.filter(f.col(self.index_column).isNull()).count()
        assert null_count == 0, \
            f'There are {null_count} null(s) in the "index_column" column in "df_labels" when no nulls are allowed.'

    def _check_nulls_in_attribute_columns(self):
        """
        Checks if nulls in attribute columns.

        :return:
        """

        columns_to_check = [col for col in self.df_labels.columns if col != self.index_column]
        row_count = self.df_labels.count()

        for col in columns_to_check:
            col_count = self.df_labels.filter(f.col(col).isNotNull()).select(col).count()

            assert col_count == row_count, f'There are null(s) in "{col}".'

    def preprocess(self):
        """
        Preprocess recipes data.

        :return: spark data frame
        """

        self._remove_columns()

        df_rectified_country_labels = self._rectify_country_labels()
        df_no_whitespaces = self._replace_whitespaces_with_underscores(df_rectified_country_labels)
        df_lower_case = self._convert_columns_to_lower_case(df_no_whitespaces)
        df_converted_nas = self._convert_nas(df_lower_case)
        df_converted_prep_time = self._convert_prep_time(df_converted_nas)
        df_one_hot = self._convert_to_one_hot(df_converted_prep_time)

        return df_one_hot

    def _remove_columns(self):
        """
        Removes columns not in self.columns

        :return:
        """

        if self.columns == 'all':
            pass
        else:
            self.df_labels = self.df_labels.select([self.index_column] + self.columns)

    def _rectify_country_labels(self):
        """
        Rectifies inconsistent country labels.

        :return: spark data frame
        """

        country_columns = [col for col in self.columns if 'country' in col]
        df_rectified_country_labels = self.df_labels

        if country_columns:
            for country in country_columns:
                df_rectified_country_labels = df_rectified_country_labels\
                    .withColumn(country, f.regexp_replace(country,
                                                          'United States of America \(USA\)',
                                                          'United States'))
                df_rectified_country_labels = df_rectified_country_labels\
                    .withColumn(country, f.regexp_replace(country,
                                                          'Israel and the Occupied Territories',
                                                          'Israel'))
                df_rectified_country_labels = df_rectified_country_labels\
                    .withColumn(country, f.regexp_replace(country,
                                                          'Korea, Republic of \(South Korea\)',
                                                          'South Korea'))

                df_rectified_country_labels = df_rectified_country_labels\
                    .withColumn(country, f.regexp_replace(country,
                                                          'Korea, Democratic Republic of \(North Korea\)',
                                                          'South Korea'))

                df_rectified_country_labels = df_rectified_country_labels\
                    .withColumn(country, f.regexp_replace(country,
                                                          'Great Britain',
                                                          'United Kingdom'))

        return df_rectified_country_labels

    def _replace_whitespaces_with_underscores(self, df_rectified_country_labels):
        """
        Replaces whitespaces with underscores in every column except "index_column"

        :param df_rectified_country_labels: spark data frame
        :return: spark data frame
        """

        columns_to_process = [col for col in df_rectified_country_labels.columns if col != self.index_column]

        df_withspaces = df_rectified_country_labels

        for col in columns_to_process:
            df_withspaces = df_withspaces.withColumn(col, f.regexp_replace(col, ' ', '_'))

        df_no_whitespaces = df_withspaces

        return df_no_whitespaces

    def _convert_columns_to_lower_case(self, df_no_whitspaces):
        """
        Converts all attriute columns to lower case.

        :param df_no_whitspaces: spark data frame
        :return: spark data frame
        """

        columns_to_process = [col for col in df_no_whitspaces.columns if col != self.index_column]

        df_lower_case = df_no_whitspaces

        for col in columns_to_process:
            df_lower_case = df_lower_case.withColumn(col, f.lower(f.col(col)))

        return df_lower_case

    def _convert_nas(self, df_lower_case):
        """
        Converts "#n/a" to column_name+not_applicable.

        :param df_lower_case: spark data frame
        :return: spark data frame
        """

        columns_to_process = [col for col in df_lower_case.columns if col != self.index_column]

        df_converted_nas = df_lower_case

        for col in columns_to_process:
            df_converted_nas = df_converted_nas.withColumn(col, f.regexp_replace(col, '#n/a', col+'_not_applicable'))

        return df_converted_nas

    def _convert_prep_time(self, df_converted_nas):
        """
        Converts prep times in ranges to upper bound of range.

        :param df_converted_nas: spark data frame
        :return: spark data frame
        """

        if 'prep_time' in self.columns:
            convert_prep_time = f.udf(lambda x: x.split('-')[-1], StringType())

            df_converted_nas = df_converted_nas.withColumn('prep_time_copy', f.col('prep_time'))

            df_converted_prep_time = df_converted_nas.withColumn('prep_time', convert_prep_time(df_converted_nas.prep_time_copy))
            df_converted_prep_time = df_converted_prep_time.drop('prep_time_copy')

            return df_converted_prep_time
        else:
            return df_converted_nas

    def _convert_to_one_hot(self, df_lower_case):
        """
        Converts recipes description data to one hot using columns attribute.

        :param df_lower_case: spark data frame
        :return: spark data frame
        """

        df_one_hot = df_lower_case

        for col in self.columns:
            unique_labels = [v[0] for v in df_lower_case.select(col).distinct().collect()]

            for label in unique_labels:
                df_one_hot = df_one_hot\
                    .withColumn(col+'_'+label, f.when(f.col(col) == label, 1).otherwise(0))

            df_one_hot = df_one_hot.drop(col)

        return df_one_hot

