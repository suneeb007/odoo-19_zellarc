FROM odoo:19.0

# Copy local addons into the image so the published image includes them
COPY ./addons /mnt/extra-addons

# Ensure proper ownership
RUN chown -R odoo:odoo /mnt/extra-addons || true

USER odoo

CMD ["/entrypoint.sh", "odoo"]
