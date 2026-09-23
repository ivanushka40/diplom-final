class ServiceError(Exception):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ForbiddenError(ServiceError):
    status_code = 403


class AuthenticationError(ServiceError):
    status_code = 401


class UserAlreadyExistsError(ServiceError):
    status_code = 400
