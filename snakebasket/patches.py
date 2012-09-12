
def patched_git_get_tag_revs(s, location):
    tags = s._get_all_tag_names(location)
    tag_revs = {}
    for line in tags.splitlines():
        tag = line.strip()
        rev = patched_git_get_revision_from_rev_parse(s, tag, location)
        tag_revs[tag] = rev.strip()
    return tag_revs

def patched_git_get_revision_from_rev_parse(s, name, location):
    from pip import call_subprocess
    ret = call_subprocess([s.cmd, 'show-ref', '--dereference', name],
        show_stdout=False, cwd=location)
    ret = ret.splitlines()[-1].split(" ")[0]
    return ret

def patched_git_get_src_requirement(self, dist, location, find_tags):
    repo = self.get_url(location)
    if not repo.lower().startswith('git:'):
        repo = 'git+' + repo
    egg_project_name = dist.egg_name().split('-', 1)[0]
    if not repo:
        return None
    current_rev = self.get_revision(location)
    tag_revs = patched_git_get_tag_revs(self, location)
    branch_revs = self.get_branch_revs(location)
    tag_name = None

    inverse_tag_revs = dict((tag_revs[key], key) for key in tag_revs.keys())
    if current_rev in inverse_tag_revs:
        # It's a tag
        tag_name = inverse_tag_revs[current_rev]
        full_egg_name = '%s' % (egg_project_name)
    elif (current_rev in branch_revs and
          branch_revs[current_rev] != 'origin/master'):
        # It's the head of a branch
        full_egg_name = '%s-%s' % (egg_project_name,
                                   branch_revs[current_rev].replace('origin/', ''))
    else:
        full_egg_name = '%s-dev' % egg_project_name

    return '%s@%s#egg=%s' % (repo, tag_name or current_rev, full_egg_name)