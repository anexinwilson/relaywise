import strawberry
from app.graphql.queries import Query
from app.graphql.mutations.user import UserMutations
from app.graphql.mutations.project import ProjectMutations


@strawberry.type
class Mutation(UserMutations, ProjectMutations):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)