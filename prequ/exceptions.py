class PrequError(Exception):
    pass


class DependencyResolutionFailed(PrequError):
    def __init__(self, ireq, pip_error, log_messages=None):
        self.ireq = ireq
        self.pip_error = pip_error
        self.log_messages = log_messages or []

    def __str__(self):
        return (
            'Dependency resolution of {self.ireq} failed:\n'
            '{self.pip_error}\n\n'
            '{error_log}').format(
                self=self, error_log='\n'.join(self.log_messages))


class NoCandidateFound(PrequError):
    def __init__(self, ireq, candidates_tried, finder):
        """
        Initialize "no candidate found" error.

        :type ireq: pip.req.InstallRequirement
        :type candidates_tried: list[pip.index.InstallationCandidate]
        """
        self.ireq = ireq
        self.candidates_tried = candidates_tried
        self.finder = finder

    def __str__(self):
        versions = []
        pre_versions = []

        for candidate in sorted(self.candidates_tried):
            version = str(candidate.version)
            if candidate.version.is_prerelease:
                pre_versions.append(version)
            else:
                versions.append(version)

        lines = [
            'Could not find a version that matches {}'.format(self.ireq),
        ]

        if versions:
            lines.append('Tried: {}'.format(', '.join(versions)))

        if pre_versions:
            if self.finder.allow_all_prereleases:
                line = 'Tried'
            else:
                line = 'Skipped'

            line += ' pre-versions: {}'.format(', '.join(pre_versions))
            lines.append(line)

        if versions or pre_versions:
            lines.append('There are incompatible versions in the resolved dependencies.')
        else:
            lines.append('No versions found')
            lines.append('{} {} reachable?'.format(
                'Were' if len(self.finder.index_urls) > 1 else 'Was', ' or '.join(self.finder.index_urls))
            )
        return '\n'.join(lines)


class UnsupportedConstraint(PrequError):
    def __init__(self, message, constraint):
        """
        Initialize "unsupported constraint" error.

        :type message: str
        :type constraint: pip.req.InstallRequirement
        """
        super(UnsupportedConstraint, self).__init__(message)
        self.constraint = constraint

    def __str__(self):
        message = super(UnsupportedConstraint, self).__str__()
        return '{} (constraint was: {})'.format(message, str(self.constraint))


class IncompatibleRequirements(PrequError):
    def __init__(self, ireq_a, ireq_b):
        """
        Initialize "incompatible requirements" error.

        :type ireq_a: pip.req.InstallRequirement
        :type ireq_b: pip.req.InstallRequirement
        """
        self.ireq_a = ireq_a
        self.ireq_b = ireq_b

    def __str__(self):
        message = "Incompatible requirements found: {} and {}"
        return message.format(self.ireq_a, self.ireq_b)


class FileOutdated(PrequError):
    pass


class WheelMissing(PrequError):
    pass
