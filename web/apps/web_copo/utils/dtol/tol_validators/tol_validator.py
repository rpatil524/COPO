import abc


class TolValidtor(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def validate(self, profile_id, json_data, data, errors, flag):
        raise NotImplemented
