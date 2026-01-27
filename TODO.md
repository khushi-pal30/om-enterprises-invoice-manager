# TODO: Add Retention Payment Option and Remove Release/Hold Concept

## Model Changes
- [ ] Modify Invoice model: Remove retention_released, retention_released_date, retention_due_date fields
- [ ] Change certified_amount property to not deduct retention (retention is always due)

## Form Changes
- [ ] Update forms.py to remove retention release fields

## View Changes
- [ ] Remove release_retention view
- [ ] Add new pay_retention view to allow paying retention separately
- [ ] Update invoices view to remove retention release logic

## Template Changes
- [ ] Update templates/edit_invoice.html: Remove retention release fields
- [ ] Update templates/invoices.html: Remove release button, add "Pay Retention" button
- [ ] Update templates/project_detail.html: Remove retention release display
- [ ] Update templates/invoice_preview.html: Remove retention release display
- [ ] Update templates/invoice_pdf.html: Remove retention release display

## Migration
- [ ] Create new migration for model changes

## Testing
- [ ] Test the changes to ensure balance due includes retention and payment works
