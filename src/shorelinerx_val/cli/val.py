from shorelinerx_val.core import validation

def main(conf):

    validation.run(
        conf.f_sx_bw,
        conf.f_insitu_bp,
        conf.odir
    )
