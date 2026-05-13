from bquer import BQuer


def run_query(bq_project_name, query_file, params=None):
    bq_creator = BQuer.create_with_project(project=bq_project_name)
    query = get_query(query_file)
    if params:
        query = replace_query_params(query, params)
    response = execute_query(bq_creator, query)
    return response

def get_query(query_file):
    with open(f"queries/{query_file}", "r") as queryFile:
        query = queryFile.read()
    return query

def replace_query_params(query, params):
    for key, value in params.items():
        query = query.replace(key, str(value))
    return query

def execute_query(bq_creator, query):
    response = bq_creator.query(
        query,
        dry_run=False,
        block=True
        )
    return response
