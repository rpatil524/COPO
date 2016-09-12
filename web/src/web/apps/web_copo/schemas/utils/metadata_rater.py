__author__ = 'etuka'

from dal.copo_da import DataFile
import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils


class MetadataRater:
    """
    class handles rating of metadata, for a designated set of items (e.g., datafiles), against different repositories
    """

    def __init__(self, item_ids=list()):
        self.item_ids = item_ids

    def rate_metadata(self, item_meta, repo):
        """
        function matches input metadata (item_meta) against a rating template, to determine an item's rating level.
        basically, the rating template is a set of sequential/mutually exclusive rules used in matching
        user description to some rating level.
        ideally, rules should be listed in a descending order of ranking (e.g., good, fair, poor)
        :param item_meta: metadata schema of the item to be rated
        :return item_rating: the resolved rating
        """

        # get repo label
        repo_name = [elem for elem in d_utils.get_repository_options() if elem["value"] == repo]

        if repo_name:
            repo_name = repo_name[0]["label"]
        else:
            repo_name = str()

        rating_template = d_utils.json_to_pytype(lkup.METADATA_RATING_TEMPLATE_LKUPS["rating_template"])["properties"]
        item_rating = dict()

        for level in rating_template:
            set_level = []
            for k, v in level["matching_rules"][repo].items():
                if v:
                    set_level.append(getattr(MetadataRater, "validate_" + k)(self, v, item_meta))

            set_level = set(set_level)
            if len(set_level) == 1 and set_level.pop():
                item_rating["rating_level"] = level["rating_level"]
                item_rating["rating_level_description"] = level["rating_level_description"].format(**locals())
                break

        return item_rating

    def get_datafiles_rating(self):
        """
        function handles the evaluation of metadata rating for datafiles
        :return: dictionary of datafiles with associated metadata rating
        """

        datafiles_rating = list()

        for df_id in self.item_ids:
            default_rating = \
                d_utils.json_to_pytype(lkup.METADATA_RATING_TEMPLATE_LKUPS["rating_template"])["properties"][-1]
            item_rating = dict()
            item_rating["rating_level"] = default_rating["rating_level"]
            item_rating["rating_level_description"] = default_rating["rating_level_description"]

            d_r = dict(item_id=df_id, item_rating=item_rating)

            attributes = DataFile().get_record_property(df_id, "description_attributes")
            deposition_context = DataFile().get_record_property(df_id, "target_repository")

            if deposition_context:
                d_r["item_rating"] = self.rate_metadata(attributes, deposition_context)

            datafiles_rating.append(d_r)

        return datafiles_rating

    def validate_allOf(self, key_list, target_schema):
        is_valid = True

        for k in key_list:
            if k not in target_schema:
                is_valid = False
                break

        return is_valid

    def validate_anyOf(self, key_list, target_schema):
        is_valid = False

        for k in key_list:
            if k in target_schema:
                is_valid = True
                break

        return is_valid

    def validate_not(self, key_list, target_schema):
        is_valid = True

        for k in key_list:
            if k in target_schema:
                is_valid = False
                break

        return is_valid
