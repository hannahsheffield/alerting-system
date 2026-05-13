import re
import pandas as pd
import bamboos.gspread_wrapper


class ChecksFormatter:

    def __init__(self,
                 control_spreadsheet_id,
                 monitoring_bq_project,
                 monitoring_bq_dataset):

        self.control_spreadsheet_id = control_spreadsheet_id
        self.monitoring_bq_project = monitoring_bq_project
        self.monitoring_bq_dataset = monitoring_bq_dataset
        self.alerts = []
        self.create_source_views_query = ""
        self.create_checks_views_query_part_1 = ""
        self.create_checks_views_query_part_2 = ""
        self.create_checks_views_query = ""

    def format_views(self):
        self.alerts = self.collect_alerts()

        self.create_checks_views_query_part_1 = self.initialise_check_view()

        for alert in self.alerts:

            self.format_query(alert)
            self.finalize_check_query()

        return None

    def collect_alerts(self):
        # collects all the queries available
        alerts = pd.read_gspread(spreadsheet_id=self.control_spreadsheet_id,
                                 worksheet_id=0,
                                 index=0,
                                 header_rows=1
                                 )

        active_alerts = (
            alerts
            .loc[
                alerts["implementation_status"] == "ACTIVE",
                :
            ]
            .to_dict(orient="records")
        )

        return active_alerts

    def initialise_check_view(self):
        check_view_init = (
            "CREATE OR REPLACE VIEW " +
            "`" +
            f"{self.monitoring_bq_project}" +
            "." +
            f"{self.monitoring_bq_dataset}" +
            "." +
            "checks" +
            "` " +
            "AS " +
            "WITH "
        )

        return check_view_init

    def format_query(self, alert):
        query_elements = self.split_query(alert["implementation_query"])
        source_query = query_elements["source"]
        check_query = query_elements["check"]

        source_temptable_id = self.get_source_temptable_id(source_query)
        check_temptable_id = self.get_check_temptable_id(check_query)

        source_view_id = (
            f"{self.monitoring_bq_project}" +
            "." +
            f"{self.monitoring_bq_dataset}" +
            "." +
            f"{source_temptable_id}"
        )

        create_source_view_sql = self.format_source_query(source_query,
                                                          source_view_id,
                                                          source_temptable_id)

        self.create_source_views_query += create_source_view_sql

        create_checks_views_sql = self.format_check_query(check_query,
                                                          source_view_id,
                                                          source_temptable_id)

        self.create_checks_views_query_part_1 += create_checks_views_sql

        create_checks_views_union_sql = (
            self.format_checks_views_union_sql(
                alert,
                check_temptable_id,
                source_view_id
            )
        )

        self.create_checks_views_query_part_2 += create_checks_views_union_sql

        return None

    def split_query(self, query):
        # separate query into source and view parts
        query_source = self.get_source(query).strip()
        query_check = self.get_check(query).strip()

        query_elements = {
            "source": query_source,
            "check":  query_check
        }

        return query_elements

    @staticmethod
    def get_source(query):
        # get index to split the query and identify the 2 pieces (source and checks)
        index_start_checks_query = (
            list(re.finditer(r"(checks_\w+ AS \()", query))[0].start(0)
        )
        source_query = query[:index_start_checks_query]

        return source_query

    @staticmethod
    def get_check(query):
        # TODO: check if there's only one check query

        # get index to split the query and identify the 2 pieces (source and checks)
        index_start_checks_query = (
            list(re.finditer(r"(checks_\w+ AS \()", query))[0].start(0)
        )
        check_query = query[index_start_checks_query:]

        return check_query

    @staticmethod
    def get_source_temptable_id(source_query):
        source_temptable_id = re.findall(r"(source_\w+) AS", source_query)[0]

        return source_temptable_id

    @staticmethod
    def get_check_temptable_id(check_query):
        check_temptable_id = re.findall(r"(checks_\w+) AS", check_query)[0]

        return check_temptable_id

    @staticmethod
    def format_source_query(query, source_view_id, source_temptable_id):
        # format source table sql to be added to one file
        view_sql = (
            f"CREATE OR REPLACE VIEW `{source_view_id}` AS " +
            query[:-1] +
            f" SELECT * FROM {source_temptable_id}; "
        )

        return view_sql

    @staticmethod
    def format_check_query(query, source_view_id, source_temptable_id):
        checks_temptable_sql = query.replace(source_temptable_id, source_view_id)

        view_sql = (
                checks_temptable_sql +
                ","
            )

        return view_sql

    @staticmethod
    def format_checks_views_union_sql(alert, check_temptable_id, source_view_id):
        union_sql = (
            "SELECT " +
            "*, " +
            f'"{source_view_id}" AS check_source, ' +
            "CURRENT_TIMESTAMP() AS check_run_timestamp, " +
            f'"{alert["looker_support"]}" AS check_looker_support, ' +
            ("FROM CHECK-TABLE ".replace("CHECK-TABLE", check_temptable_id)) +
            "UNION ALL "
        )

        return union_sql

    def finalize_check_query(self):
        create_checks_views_query = (
            # removing the last 1 character is needed to remove the last comma (,)
            self.create_checks_views_query_part_1[:-1] +
            " " +
            # removing the last 11 characters is needed to remove the last UNION ALL
            self.create_checks_views_query_part_2[:-11]
        )

        self.create_checks_views_query = create_checks_views_query

        return None
