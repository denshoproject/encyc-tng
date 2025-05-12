# encyc-tng

Densho Encyclopedia: The Next Generation

## Documentation

- [Technical Documentation](docs/index.md)
- [Front-end Tooling Guide](docs/front-end/tooling.md)
- [Docker Development Environment](docs/docker.md)

## Package Management

### Keeping Dependencies Up to Date

This project uses npm for package management. There are several ways to keep dependencies up to date:

1. **GitHub Dependabot (Recommended)**

   - Dependabot automatically creates pull requests to update dependencies
   - It checks for security vulnerabilities and outdated packages
   - Pull requests include detailed information about the updates

2. **Manual Updates**

   ```bash
   # Check for outdated packages
   npm outdated

   # Update all packages to their latest version
   npm update

   # Update a specific package
   npm update <package-name>
   ```

3. **Security Audits**

   ```bash
   # Run security audit
   npm audit

   # Fix security vulnerabilities automatically
   npm audit fix

   # Fix security vulnerabilities and update package versions
   npm audit fix --force
   ```

Note: After updating packages, make sure to:

- Test the application thoroughly
- Review the changelog of major version updates
- Check for any breaking changes
