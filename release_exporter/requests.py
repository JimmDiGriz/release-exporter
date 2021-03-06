import json

import requests

from release_exporter.base import FormatBase
from release_exporter.exceptions import InvalidToken
from release_exporter.utils import get_repo_url_info, multi_key_gitlab


class GitHubRequest(FormatBase):
    """
    GitHub request base.
    """

    def __init__(self, *args, **kwargs):
        super(GitHubRequest, self).__init__(*args, **kwargs)
        self.request_headers = {'Authorization': 'token %s' % self.token}
        self.api_url = 'https://api.github.com/graphql'

        if self.token is None:
            raise InvalidToken(
                "Oops! GitHub requires you to generate a private token to get the details. See "
                "https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/ "
                "for more information.")

        if self.repo_url is not None:
            self.info = get_repo_url_info(self.location, repo_url=self.repo_url)
        else:
            self.info = get_repo_url_info(self.location)

    def _total_number_releases(self):
        """
        Queries total number of releases.

        Returns
        -------
        int: int
            Number of releases.
        """
        _json = {"query": """
            {
              repository(owner: """ + """\"{}\",""".format(self.info.owner) + """ name: """ + """\"{}\")""".format(
            self.info.name) + """ {
                releases {
                  totalCount
                }
              }
            }
        """}

        response = json.loads(requests.post(url=self.api_url, json=_json, headers=self.request_headers).text)

        if response['errors'] is not None:
            messages = ''
            for error in response['errors']:
                messages += error['message'] + '; '

            raise Exception(messages)

        try:
            return int(response['data']['repository']['releases']['totalCount'])
        except KeyError:
            raise KeyError('Wrong credentials given. Please check if you have the correct token.')

    def releases(self):
        """
        A JSON object with name of the repository, tag name, description and the created date and time.

        Returns
        -------
        JSON: dict
            A JSON object.
        """
        _json = {
            "query": """
                query {""" +
                     """repository(owner: \"{}\", name: \"{}\") """.format(self.info.owner, self.info.name) + """{
                    releases(""" + """first:{}""".format(self._total_number_releases()) + """, orderBy: {field: CREATED_AT, direction: DESC}){
                      edges{
                        node{
                          name
                          author {
                            login
                          }
                          tag{
                            name
                          }
                          description
                          createdAt
                        }
                      }
                    }
                  }
                }
            """
        }

        r = requests.post(url=self.api_url, json=_json, headers=self.request_headers)
        return json.loads(r.text)


class GitLabRequest(FormatBase):
    """
    GitLab request base.
    """

    def __init__(self, *args, **kwargs):
        super(GitLabRequest, self).__init__(*args, **kwargs)
        self.request_headers = {'Private-Token': '%s' % self.token}
        self.api_url = 'https://gitlab.com/api/v4/'

        if self.token is None:
            raise InvalidToken(
                "Oops! GitLab requires you to generate a private token to get the details. See "
                "https://docs.gitlab.com/ce/user/profile/personal_access_tokens.html "
                "for more information.")

        if self.repo_url is not None:
            self.info = get_repo_url_info(self.location, repo_url=self.repo_url)
        else:
            self.info = get_repo_url_info(self.location)

    def _repo_id(self):
        """
        Searches and returns the repository ID based on the repository name. If the repository is not found then a table
        of repository is shown so that the user can manually enter the ID of their repository.

        Returns
        -------
        id_number: int
            Repository ID.

        """
        url = self.api_url + 'projects?search={}'.format(self.info.name)

        r = requests.get(url=url, headers=self.request_headers)
        id_number = json.loads(r.text)

        if len(id_number) > 1:
            print(
                "The search resulted in more that one repository. Please check your repository name and type in it's ID")
            print('ID - Repository Name - Username')

            for content in id_number:
                print('{id} - {repo_name} - {user_name}'.format(id=content['id'], repo_name=content['name'],
                                                                user_name=multi_key_gitlab(content)))

            id_number = input('ID > ')
            return id_number

        try:
            return id_number[0]['id']
        except KeyError:
            raise KeyError('Wrong credentials given. Please check if you have the correct token.')

    def releases(self):
        """
        A JSON object containing name of the repository, tag name, description and the created date and time

        Returns
        -------
        JSON: dict
            A dict object.
        """
        url = 'https://gitlab.com/api/v4/projects/{id}/repository/tags'.format(id=self._repo_id())

        r = requests.get(url=url, headers=self.request_headers)
        return json.loads(r.text)
