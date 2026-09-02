# Contributing to Fleet Status Dashboard

Guidelines for contributing to the OpenShift Fleet Status Dashboard project.

## Code of Conduct

Treat everyone with respect. We aim to maintain a welcoming and inclusive community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USER/fleet-status.git`
3. Create a feature branch: `git checkout -b feature/my-feature`
4. Make your changes
5. Push to your fork
6. Open a Pull Request

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export MOCK_MODE=true
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if added)
cd ../frontend
npm test
```

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Keep functions small and focused
- Use meaningful variable names
- Add docstrings to public methods

Example:
```python
async def get_cluster_metrics(cluster_id: str) -> Optional[ClusterMetrics]:
    """Get metrics for a specific cluster."""
    try:
        result = await thanos_client.query(f'acm_managed_cluster_info{{cluster="{cluster_id}"}}')
        # ...
    except Exception as e:
        logger.error(f"Error fetching metrics for {cluster_id}: {e}")
        return None
```

### TypeScript/React (Frontend)

- Use functional components with hooks
- Use TypeScript for type safety
- Keep components focused and reusable
- Use consistent naming (PascalCase for components)

Example:
```typescript
interface ClusterCardProps {
  cluster: ClusterMetrics;
  onSelect?: (id: string) => void;
}

export function ClusterCard({ cluster, onSelect }: ClusterCardProps) {
  return (
    <div onClick={() => onSelect?.(cluster.id)}>
      {/* Card content */}
    </div>
  );
}
```

## Commit Messages

Use clear, descriptive commit messages:

```
[component] Brief description

Detailed explanation of changes if needed.

Fixes #123 (if applicable)
Co-Authored-By: Name <email>
```

Examples:
- `[backend] Add CPU sustained metric calculation`
- `[frontend] Fix cluster card rendering on mobile`
- `[infra] Update OpenShift deployment specs`

## Pull Request Guidelines

1. **Title**: Start with [backend], [frontend], [infra], or [docs]
2. **Description**: Explain what changed and why
3. **Testing**: Describe manual testing performed
4. **Screenshots**: Include if UI changes
5. **Breaking changes**: Clearly mark any breaking changes

Example PR description:
```markdown
## Changes
- Add memory capacity metrics to cluster view
- Improve caching strategy for large fleets

## Testing
- Verified with 50 clusters in mock mode
- Checked memory calculations against Thanos directly

## Screenshots
[Screenshot of updated cluster card]

## Notes
No breaking API changes
```

## Areas for Contribution

### Backend
- [ ] Additional metrics and calculations
- [ ] Performance optimizations
- [ ] Error handling improvements
- [ ] Unit and integration tests
- [ ] Documentation
- [ ] New API endpoints

### Frontend
- [ ] Additional dashboard views
- [ ] Cluster detail drill-down pages
- [ ] Time-series graph components
- [ ] Alert management interface
- [ ] Dark/light theme selector
- [ ] E2E tests

### Infrastructure
- [ ] Helm chart
- [ ] CI/CD pipeline improvements
- [ ] Monitoring and alerting
- [ ] Multi-cluster deployment
- [ ] HA/load balancing setup

### Documentation
- [ ] Troubleshooting guides
- [ ] Architecture diagrams
- [ ] Video tutorials
- [ ] API documentation
- [ ] Deployment walkthroughs

## Testing Requirements

All pull requests should include:

1. **Manual testing**: Describe what was tested locally
2. **Unit tests**: For new functions/components
3. **Integration tests**: For backend changes
4. **Error cases**: Verify graceful degradation

For significant changes:
- Test with MOCK_MODE=true and actual Thanos
- Verify with multiple clusters (10+)
- Check performance with large datasets

## Documentation

Update documentation for:
- New API endpoints
- New configuration options
- Changed behavior
- Known limitations
- Migration guides (if breaking changes)

Use clear, concise language. Include examples.

## Reporting Issues

Use GitHub Issues with:

1. **Title**: Clear description of the problem
2. **Environment**: 
   - RHACM version
   - Cluster count
   - OS/browser (for frontend)
3. **Steps to reproduce**: Exact steps
4. **Expected vs actual**: What should happen vs what happened
5. **Logs**: Relevant error messages or backend logs
6. **Screenshots**: Visual issues

Example issue:
```markdown
## Description
Fleet status shows "CRITICAL" for healthy clusters

## Environment
- RHACM: 2.8.0
- Clusters: 15
- Browser: Firefox 120

## Steps to Reproduce
1. Deploy dashboard with 15 managed clusters
2. Navigate to dashboard
3. Observe cluster status

## Expected
Clusters with no alerts show "HEALTHY"

## Actual
All clusters show "CRITICAL"

## Logs
```
Backend error: metrics_service.py:145 Error getting alerts: connection refused
```

## Release Process

Releases follow semver (X.Y.Z):

- **X**: Major (breaking changes)
- **Y**: Minor (new features)
- **Z**: Patch (bug fixes)

Tag releases: `git tag v1.2.3`

## Questions?

- Open a discussion in GitHub Discussions
- Check existing issues/PRs
- Review METRICS_REFERENCE.md
- Check INTEGRATION_GUIDE.md

## Thank You

Contributions make this project better. Thank you for your interest!
