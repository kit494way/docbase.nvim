import docbase
import neovim


@neovim.plugin
class DocBaseNvim(object):

    def __init__(self, vim):
        self.vim = vim
        self.buffer = None
        docbase.config.team = self._get_gvar('team')
        docbase.config.api_token = self._get_gvar('api_token')

    @neovim.command('DocBaseOpen', nargs='1', sync=True)
    def open(self, args):
        self.vim.command('echo "Loading ..."')
        post_id = args[0]
        post = docbase.posts(post_id)
        self._show_single_buffer('[DocBase:{}]'.format(post_id))
        self.vim.command('set filetype=markdown')
        self.buffer = self.vim.current.buffer
        self._to_buffer(post)
        self.vim.current.window.cursor = (1, 0)

    @neovim.command('DocBaseSave', nargs='?', sync=True)
    def save(self, args):
        self.vim.command('echo "Saving ..."')
        self.buffer = self.vim.current.buffer
        if len(args) > 0:
            self._set_bvar('title', args[0])

        post = self._from_buffer()
        if post.id:
            post = docbase.update(post)
        else:
            post = docbase.create(post)

        self.vim.command('echom "saved url {}"'.format(post.url))
        self._to_buffer(post, ignore_body=True)

    @neovim.command('DocBaseSearch', nargs='*')
    def search(self, args):
        self.vim.command('echo "Searching ..."')
        query = ' '.join(args) if len(args) > 0 else None
        posts = docbase.posts(query=query)
        self._store_search_result(posts)
        self.vim.command('DocBaseSearchResult')

    @neovim.command('DocBaseSearchNext')
    def search_next(self):
        self.vim.command('echo "Searching ..."')
        url = self._get_gvar('search_next')
        if url is None:
            self.vim.command('echo "No next"')
            return
        posts = docbase.posts(url=url)
        self._store_search_result(posts)
        self.vim.command('DocBaseSearchResult')

    @neovim.command('DocBaseSearchPrev')
    def search_prev(self):
        self.vim.command('echo "Searching ..."')
        url = self._get_gvar('search_prev')
        if url is None:
            self.vim.command('echo "No previous"')
            return
        posts = docbase.posts(url=url)
        self._store_search_result(posts)
        self.vim.command('DocBaseSearchResult')

    @neovim.command('DocBaseSearchResult', sync=True)
    def search_result(self):
        result = self._get_gvar('search_result', [])
        if len(result) == 0:
            self.vim.command('echo "Not Found"')
            return

        self._show_single_buffer('[DocBaseSearch]')
        self.vim.command('setlocal modifiable')
        self.vim.current.buffer[:] = [post['title'] for post in result]
        self.vim.command('setlocal nomodified nomodifiable')
        self.vim.current.window.cursor = (1, 0)

        self.vim.command('nnoremap <buffer> <Enter> :DocBaseOpenResult<Enter>')

    @neovim.command('DocBaseOpenResult', range='')
    def open_result(self, range):
        post = self._get_gvar('search_result')[range[0] - 1]
        self.vim.command('DocBaseOpen {}'.format(post['id']))

    @neovim.command('DocBaseTitle', nargs='?')
    def title(self, args):
        self._property_command('title', args)

    @neovim.command('DocBaseAddTags', nargs='+')
    def add_tags(self, args):
        self.buffer = self.vim.current.buffer
        tags = self._get_bvar('tags', [])
        tags.extend(args)
        self._set_bvar('tags', tags)
        self.vim.command('echo "Tags: {}"'.format(', '.join(tags)))

    @neovim.command('DocBaseRemoveTags', nargs='+')
    def remove_tags(self, args):
        self.buffer = self.vim.current.buffer
        tags = self._get_bvar('tags')
        tags = [tag for tag in tags if tag != args[0]]
        self._set_bvar('tags', tags)
        self.vim.command('echo "Tags: {}"'.format(', '.join(tags)))

    @neovim.command('DocBaseDraftEnable')
    def draft_enable(self):
        self._property_command('draft', [True])

    @neovim.command('DocBaseDraftDisable')
    def draft_disable(self):
        self._property_command('draft', [False])

    @neovim.command('DocBaseScope', nargs='*')
    def scope(self, args):
        self._property_command('scope', args)
        if len(args) > 0 and args[0] == 'group':
            self._set_bvar('groups', args[1:])

    @neovim.command('DocBaseNoticeEnable')
    def notice_enable(self):
        self._property_command('notice', [True])

    @neovim.command('DocBaseNoticeDisable')
    def notice_disable(self):
        self._property_command('notice', [False])

    @neovim.command('DocBaseInfo')
    def info(self):
        self.buffer = self.vim.current.buffer
        info = ['{}: {}'.format(key, self._get_bvar(key)) for key
                in ['author', 'title', 'url', 'scope', 'id', 'draft',
                    'notice']]

        info.append('tags: {}'.format(', '.join(self._get_bvar('tags', []))))

        if self._get_bvar('scope') == 'group':
            info.append('groups: {}'.format(self._get_bvar('groups', [])))

        info.append('comments:')
        for comment in self._get_bvar('comments', []):
            comment_message = comment['message'].splitlines()
            lines = ['  - {}'.format(comment_message[0])]
            lines.extend(['    {}'.format(line)
                          for line in comment_message[1:]])
            lines.append('    written by {}, at {}'.format(
                comment['user'], comment['created_at']))
            lines.append('')
            info.extend(lines)

        self._show_single_buffer('[DocBaseInfo]')
        self.vim.command('setlocal modifiable')
        self.vim.current.buffer[:] = info
        self.vim.command('setlocal nomodified nomodifiable')
        self.vim.current.window.cursor = (1, 0)

    def _to_buffer(self, post, ignore_body=False):
        for key in ['id', 'url', 'title', 'draft', 'notice', 'scope']:
            self._set_bvar(key, getattr(post, key))

        self._set_bvar('author', post.user.name)
        self._set_bvar('tags', [str(tag) for tag in post.tags])

        if post.scope == 'group':
            self._set_bvar('groups', [str(group) for group in post.groups])

        self._set_bvar('comments',
                       [{'message': comment.body, 'user': comment.user.name,
                         'created_at': comment.created_at}
                        for comment in post.comments])

        if not ignore_body:
            self.buffer[:] = post.body.splitlines()

    def _from_buffer(self):
        bvars = {key: self._get_bvar(key)
                 for key
                 in ['id', 'title', 'draft', 'notice', 'scope', 'tags']}
        post_props = {k: v for k, v in bvars.items() if v is not None}
        post = docbase.Post(**post_props)
        post.body = '\r\n'.join(self.buffer)

        if post.scope == 'group':
            all_groups = docbase.groups()
            groups = [self._find_group_from(name, all_groups)
                      for name in self._get_bvar('groups')]
            errors = [e for e in groups if isinstance(e, UnknownGroupError)]
            if len(errors) > 0:
                raise errors[0]
            post.groups = groups

        return post

    def _find_group_from(self, name, groups):
        return next(filter(lambda x: x.name == name, groups),
                    UnknownGroupError(name))

    def _set_gvar(self, key, value):
        self.vim.api.set_var('docbase_{}'.format(key), value)

    def _get_gvar(self, key, default=None):
        try:
            return self.vim.api.get_var('docbase_{}'.format(key))
        except neovim.api.nvim.NvimError:
            return default

    def _set_bvar(self, key, value):
        self.buffer.api.set_var('docbase_{}'.format(key), value)

    def _get_bvar(self, key, default=None):
        try:
            return self.buffer.api.get_var('docbase_{}'.format(key))
        except neovim.api.nvim.NvimError:
            return default

    def _store_search_result(self, posts):
        self._set_gvar('search_result',
                       [{'title': post.title, 'id': post.id}
                        for post in posts])
        self._set_gvar('search_prev', posts.previous_page)
        self._set_gvar('search_next', posts.next_page)
        self._set_gvar('search_total', posts.total)

    def _property_command(self, key, args):
        self.buffer = self.vim.current.buffer
        if len(args) > 0:
            self._set_bvar(key, args[0])

        self.vim.command('echom "DocBase{} : {}"'.format(
            key.capitalize(), self._get_bvar(key)))

    def _show_single_buffer(self, buffer_name):
        windows = [w for w in self.vim.current.tabpage.windows
                   if w.buffer.name.endswith(buffer_name)]
        if len(windows) > 0:
            self.vim.current.window = windows[0]
            return

        buffers = [b for b in self.vim.buffers
                   if b.name.endswith(buffer_name)]
        if len(buffers) > 0:
            self.vim.current.buffer = buffers[0]
            return

        self.vim.command((
            'enew | '
            'setlocal buftype=nofile bufhidden=hide noswapfile | '
            'file {}')
            .format(buffer_name))


class Error(Exception):
    pass


class UnknownGroupError(Error):
    def __init__(self, name):
        super().__init__('Unknown Group name : {}'.format(name))
