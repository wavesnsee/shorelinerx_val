from shorelinerx_val.core import validation

def main(conf):

    validation.run(
        conf.sdi.path,
        conf.sdi.id,
        conf.sdi.color,
        conf.f_insitu_bp,
        conf.f_tr,
        conf.table_tr_id,
        conf.site,
        conf.val_metrics_unit,
        conf.pixel_res,
        conf.tide_selection,
        conf.odir
    )
